"""Choose a course by track, surface, and distance, and build a RaceRequest.

Condition enums use the names shown in the Global client; their values are the
strings the engine accepts. Ground is the one that differs: the engine uses the
JP-derived names, so Global "Firm" is sent as 'Good' and Global "Good" as 'Yielding'.
"""
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from enum import Enum, IntEnum
from typing import Iterable, Optional, Union

from .builder import Strategy, UmaBuilder, _display_name
from .courses import _CHAMPIONS_MEETINGS, _COURSES, ChampionsMeeting, Track
from .enums import _BUNDLED_SKILL_IDS, Skill, Uma
from .models import RaceRequest, Runner

_BUNDLED_IDS = frozenset(map(str, _BUNDLED_SKILL_IDS))


def _wire_skill_id(entry) -> str:
    """The table key the engine looks up for a runner's skill entry."""
    value = entry.get('skillId') if isinstance(entry, dict) else entry
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(int(value))
    return repr(value)


def _skill_name(skill_id: str) -> str:
    try:
        return f'{_display_name(Skill(int(skill_id)))} #{skill_id}'
    except ValueError:
        return f'#{skill_id}'


def _is_inherited(skill_id: str) -> bool:
    try:
        return Skill(int(skill_id)).is_inherited
    except ValueError:
        return False


class Surface(IntEnum):
    TURF = 1
    DIRT = 2


class DistanceCategory(IntEnum):
    SPRINT = 1
    MILE = 2
    MEDIUM = 3
    LONG = 4


class Layout(IntEnum):
    NONE = 1
    INNER = 2
    OUTER = 3
    OUTER_TO_INNER = 4


class Turn(IntEnum):
    RIGHT = 1  # clockwise
    LEFT = 2  # counterclockwise
    STRAIGHT = 4


class Ground(str, Enum):
    """Global ground names; values are the engine's JP-derived names."""
    FIRM = 'Good'
    GOOD = 'Yielding'
    SOFT = 'Soft'
    HEAVY = 'Heavy'


class Weather(str, Enum):
    SUNNY = 'Sunny'
    CLOUDY = 'Cloudy'
    RAINY = 'Rainy'
    SNOWY = 'Snowy'


class Season(str, Enum):
    SPRING = 'Spring'
    SUMMER = 'Summer'
    AUTUMN = 'Autumn'
    WINTER = 'Winter'
    SAKURA = 'Sakura'


class Time(str, Enum):
    MORNING = 'Morning'
    MIDDAY = 'Midday'
    EVENING = 'Evening'
    NIGHT = 'Night'


class Grade(str, Enum):
    G1 = 'G1'
    G2 = 'G2'
    G3 = 'G3'
    OP = 'OP'
    PRE_OP = 'Pre-OP'
    MAIDEN = 'Maiden'
    DEBUT = 'Debut'
    DAILY = 'Daily'


def _title(member: Enum) -> str:
    return member.name.replace('_', ' ').title()


@dataclass(frozen=True)
class Course:
    id: int
    track: Track
    surface: Surface
    distance: int
    category: DistanceCategory
    layout: Layout
    turn: Turn

    @classmethod
    def get(cls, course_id: int) -> 'Course':
        if type(course_id) is not int or course_id not in _COURSES:
            raise ValueError(f'Unknown course ID: {course_id!r}')
        track, surface, distance, category, layout, turn = _COURSES[course_id]
        return cls(course_id, Track(track), Surface(surface), distance,
                   DistanceCategory(category), Layout(layout), Turn(turn))

    @classmethod
    def all(cls) -> 'list[Course]':
        return [cls.get(course_id) for course_id in _COURSES]

    @classmethod
    def find(cls, track: Track, surface: Surface, distance: int,
             layout: Optional[Layout] = None) -> 'Course':
        """Return the single course matching track, surface, distance (and layout)."""
        track, surface = Track(track), Surface(surface)
        if layout is not None:
            layout = Layout(layout)
        if type(distance) is not int:
            raise TypeError('distance must be an integer number of meters')
        on_surface = [c for c in cls.all() if c.track == track and c.surface == surface]
        matches = [c for c in on_surface if c.distance == distance
                   and (layout is None or c.layout == layout)]
        if not matches:
            options = ', '.join(f'{c.distance}m' + ('' if c.layout == Layout.NONE else f' {_title(c.layout).lower()}')
                                for c in sorted(on_surface, key=lambda c: (c.distance, c.layout)))
            raise ValueError(f'No {track.label} {_title(surface).lower()} course of {distance}m'
                             + (f' with layout {layout.name}' if layout else '')
                             + (f'; available: {options}' if options else ''))
        if len(matches) > 1:
            choices = ', '.join(f'#{c.id} ({c.layout.name})' for c in matches)
            hint = ('pass layout=' if len({c.layout for c in matches}) == len(matches)
                    else 'use RaceBuilder.from_course with one of the IDs')
            raise ValueError(f'{len(matches)} courses match {track.label} {_title(surface)} '
                             f'{distance}m: {choices}; {hint}')
        return matches[0]

    def __str__(self) -> str:
        layout = '' if self.layout == Layout.NONE else f' {_title(self.layout).lower()}'
        turn = 'straight' if self.turn == Turn.STRAIGHT else f'{_title(self.turn).lower()}-handed'
        return (f'{self.track.label} {_title(self.surface)} {self.distance}m{layout} '
                f'({_title(self.category)}, {turn})')


@dataclass(frozen=True)
class RacePreset:
    name: str
    date: date
    course: Course
    season: Season
    ground: Ground
    weather: Weather
    time: Time

    @classmethod
    def champions_meeting(cls, cm: ChampionsMeeting) -> 'RacePreset':
        if not isinstance(cm, ChampionsMeeting):
            raise TypeError('cm must be a ChampionsMeeting member')
        when, course_id, season, ground, weather, time = _CHAMPIONS_MEETINGS[cm.value]
        return cls(cm.label, date.fromisoformat(when), Course.get(course_id), Season(season),
                   Ground(ground), Weather(weather), Time(time))

    @classmethod
    def all_champions_meetings(cls) -> 'list[RacePreset]':
        """Every Global Champions Meeting preset, oldest first."""
        return sorted((cls.champions_meeting(cm) for cm in ChampionsMeeting), key=lambda p: p.date)


class RaceBuilder:
    def __init__(self, track: Track, surface: Surface, distance: int, *,
                 layout: Optional[Layout] = None):
        self._reset(Course.find(track, surface, distance, layout))

    def _reset(self, course: Course):
        self._course = course
        self._preset = None
        self._ground = Ground.FIRM
        self._weather = Weather.SUNNY
        self._season = Season.SPRING
        self._time = Time.MIDDAY
        self._grade = Grade.G1
        self._seed = None
        self._runners = []
        self._skill_data = None

    @classmethod
    def from_course(cls, course: Union[Course, int]) -> 'RaceBuilder':
        result = cls.__new__(cls)
        result._reset(course if isinstance(course, Course) else Course.get(course))
        return result

    @classmethod
    def champions_meeting(cls, cm: ChampionsMeeting) -> 'RaceBuilder':
        preset = RacePreset.champions_meeting(cm)
        result = cls.from_course(preset.course)
        result._preset = preset
        result._ground, result._weather = preset.ground, preset.weather
        result._season, result._time = preset.season, preset.time
        return result

    @property
    def course(self) -> Course:
        return self._course

    def ground(self, ground: Ground):
        # Raw strings are ambiguous here ('Good' is Global Firm), so require a member.
        if not isinstance(ground, Ground):
            raise TypeError('ground must be a Ground member, e.g. Ground.FIRM')
        self._ground = ground
        return self

    def weather(self, weather: Weather):
        self._weather = Weather(weather)
        return self

    def season(self, season: Season):
        self._season = Season(season)
        return self

    def time(self, time: Time):
        self._time = Time(time)
        return self

    def grade(self, grade: Grade):
        self._grade = Grade(grade)
        return self

    def seed(self, seed: int):
        if type(seed) is not int or not -2 ** 63 <= seed < 2 ** 63:
            raise ValueError('seed must be a 64-bit integer')
        self._seed = seed
        return self

    def runner(self, runner: Union[Runner, UmaBuilder]):
        """Add a runner; an UmaBuilder is built now, so later edits to it don't apply."""
        if isinstance(runner, UmaBuilder):
            runner = runner.build()
        elif isinstance(runner, Runner):
            runner = deepcopy(runner)
        else:
            raise TypeError('runner must be a Runner or UmaBuilder')
        self._runners.append(runner)
        return self

    def runners(self, runners: Iterable[Union[Runner, UmaBuilder]]):
        for runner in runners:
            self.runner(runner)
        return self

    def skill_data(self, table: Optional[dict]):
        """Send a replacement skill table as `skillData`; None uses the bundled table.

        The table is copied now and shared (not copied) by each built request.
        """
        if table is not None and not isinstance(table, dict):
            raise TypeError('skill table must be a dict keyed by skill ID, or None')
        self._skill_data = deepcopy(table)
        return self

    def unknown_skills(self) -> 'list[tuple[int, str]]':
        """(runner index, skill ID) for skills missing from the table this race uses.

        The engine silently ignores such skills, so build() rejects them by default.
        """
        known = (_BUNDLED_IDS if self._skill_data is None
                 else {str(k) for k in self._skill_data})
        return [(i, sid) for i, runner in enumerate(self._runners)
                for sid in map(_wire_skill_id, runner.extra.get('skills') or [])
                if sid not in known]

    def build(self, *, allow_unknown_skills: bool = False) -> RaceRequest:
        if self._seed is None:
            raise ValueError('Set a seed before building')
        if not self._runners:
            raise ValueError('Add at least one runner before building')
        unknown = [] if allow_unknown_skills else self.unknown_skills()
        if unknown:
            table = 'bundled skill table' if self._skill_data is None else 'supplied skill_data table'
            listed = '; '.join(f'runner {i} ({_runner_name(self._runners[i])}): {_skill_name(sid)}'
                               for i, sid in unknown)
            hint = ''
            if any(_is_inherited(sid) for _, sid in unknown):
                hint = (' Inherited versions of newer uniques have no definition in the bundled '
                        'table; only a supplied table that defines them can simulate them.')
            raise ValueError(f'{len(unknown)} skill(s) are not in the {table}, so the engine would '
                             f'silently ignore them: {listed}.{hint} Use skill_data() to supply a '
                             'table that defines them, or build(allow_unknown_skills=True).')
        extra = dict(time=self._time.value, grade=self._grade.value)
        if self._skill_data is not None:
            extra['skillData'] = self._skill_data
        return RaceRequest(self._seed, self._course.id, self._ground.value, self._weather.value,
                           self._season.value, deepcopy(self._runners), extra)

    def _matches_preset(self) -> bool:
        p = self._preset
        return p is not None and (p.course, p.ground, p.weather, p.season, p.time) == (
            self._course, self._ground, self._weather, self._season, self._time)

    def __str__(self) -> str:
        if self._matches_preset():
            title = f'{self._preset.name} ({self._preset.date.isoformat()})'
        else:
            title = str(self._course)
        conditions = ', '.join(_title(c) for c in (self._ground, self._weather, self._season, self._time))
        lines = [title,
                 f'  Course      {self._course} #{self._course.id}',
                 f'  Conditions  {conditions}, {self._grade.value}',
                 f'  Seed        {"(not set)" if self._seed is None else self._seed}',
                 f'  Runners     {len(self._runners) or "none"}']
        for i, runner in enumerate(self._runners, 1):
            lines.append(f'    {i}. {_runner_name(runner)}')
        return '\n'.join(lines)


def _runner_name(runner: Runner) -> str:
    try:
        name = Uma(runner.extra.get('charaId')).label
    except ValueError:
        name = 'Runner'
    try:
        return f'{name} ({_title(Strategy(runner.strategy))})'
    except ValueError:
        return f'{name} ({runner.strategy})'
