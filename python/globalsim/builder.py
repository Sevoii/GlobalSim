"""Construct a GlobalSim Runner from trained stats and explicit aptitudes."""
from copy import deepcopy
from enum import Enum
import math
import json
from .models import Runner
from .enums import Skill, Uma


class Strategy(str, Enum):
    FRONT_RUNNER = 'Nige'
    PACE_CHASER = 'Senkou'
    LATE_SURGER = 'Sasi'
    END_CLOSER = 'Oikomi'
    RUNAWAY = 'Oonige'


class Aptitude(str, Enum):
    S = 'S'
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'
    E = 'E'
    F = 'F'
    G = 'G'


_MOODS = {-2: 'Awful', -1: 'Bad', 0: 'Normal', 1: 'Good', 2: 'Great'}
_STATS = (('speed', 'Speed'), ('stamina', 'Stamina'), ('power', 'Power'),
          ('guts', 'Guts'), ('wisdom', 'Wit'))
_APTITUDES = (('distance_aptitude', 'Distance'), ('surface_aptitude', 'Surface'),
              ('strategy_aptitude', 'Strategy'))


def _number(value):
    return str(value) if isinstance(value, int) else f'{value:g}'


class UmaBuilder:
    def __init__(self, uma: Uma):
        if not isinstance(uma, Uma):
            raise TypeError('uma must be a Uma enum member')
        self._uma = uma
        self._stats = None
        self._strategy = None
        self._aptitudes = None
        self._skills = {}
        self._mood = 0
        self._extra = {}

    @classmethod
    def from_json(cls, value) -> 'UmaBuilder':
        """Load a runner JSON string, bytes, or dictionary.

        Character and skill IDs must exist in the bundled enums. Missing mood
        defaults to zero. Extra runner and skill fields are retained.
        """
        if isinstance(value, (str, bytes, bytearray)):
            value = json.loads(value)
        if not isinstance(value, dict):
            raise TypeError('Runner JSON must be an object')
        value = deepcopy(value)
        try:
            chara_id = value['charaId']
            if type(chara_id) is not int:
                raise ValueError('charaId must be an integer')
            result = cls(Uma(chara_id))
            result.stats(**{k: value[k] for k in ('speed', 'stamina', 'power', 'guts', 'wisdom')})
            result.strategy(value['strategy'])
            result.aptitudes(distance=value['distanceAptitude'],
                             surface=value['surfaceAptitude'], strategy=value['strategyAptitude'])
            result.mood(value.get('mood', 0))
            skills = value.get('skills', [])
            if not isinstance(skills, list):
                raise ValueError('skills must be an array')
            for entry in skills:
                raw_id = entry.get('skillId') if isinstance(entry, dict) else entry
                if not (type(raw_id) is int or isinstance(raw_id, str) and raw_id.isdecimal()):
                    raise ValueError('skillId must be an integer or decimal string')
                skill = Skill(int(raw_id))
                if isinstance(entry, dict):
                    result.skill(skill, level=entry.get('level', 1), unique=entry.get('isUnique', False))
                    # Keep extra fields, but emit the canonical ID the engine looks up.
                    result._skills[int(skill)].update(entry, skillId=str(int(skill)))
                else:
                    result.skill(skill)
            known = {'speed', 'stamina', 'power', 'guts', 'wisdom', 'strategy',
                     'distanceAptitude', 'surfaceAptitude', 'strategyAptitude',
                     'charaId', 'mood', 'skills'}
            result._extra = {k: v for k, v in value.items() if k not in known}
            return result
        except KeyError as error:
            raise ValueError(f'Missing runner field: {error.args[0]}') from error

    def to_json(self, indent: int = 2) -> str:
        """Return runner JSON accepted by from_json; requires a complete builder."""
        return json.dumps(self.build().to_dict(), indent=indent, ensure_ascii=False, allow_nan=False)

    def __str__(self) -> str:
        """Return a readable summary; unset sections are shown as such."""
        lines = [f'{self._uma.label} (#{int(self._uma)})']

        def row(name, value):
            lines.append(f'  {name:<10} {value}')

        unset = '(not set)'
        row('Strategy', unset if self._strategy is None else
            Strategy(self._strategy).name.replace('_', ' ').title())
        row('Mood', f'{_MOODS[self._mood]} ({self._mood:+d})')
        row('Stats', unset if self._stats is None else '  '.join(
            f'{label} {_number(self._stats[key])}' for key, label in _STATS))
        row('Aptitudes', unset if self._aptitudes is None else '  '.join(
            f'{label} {self._aptitudes[key]}' for key, label in _APTITUDES))
        if self._skills:
            row('Skills', len(self._skills))
            names = {key: Skill(key).label for key in self._skills}
            width = max(map(len, names.values()))
            for key, entry in self._skills.items():
                unique = '  unique' if entry['isUnique'] else ''
                lines.append(f'    {names[key]:<{width}}  #{key:<9}  Lv{entry["level"]}{unique}')
        else:
            row('Skills', 'none')
        if self._extra:
            row('Extra', ', '.join(sorted(self._extra)))
        return '\n'.join(lines)

    def stats(self, *, speed, stamina, power, guts, wisdom):
        values = dict(speed=speed, stamina=stamina, power=power, guts=guts, wisdom=wisdom)
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
               not math.isfinite(v) or v < 0 for v in values.values()):
            raise ValueError('Stats must be finite nonnegative numbers')
        self._stats = values
        return self

    def strategy(self, strategy: Strategy):
        self._strategy = Strategy(strategy).value
        return self

    def aptitudes(self, *, distance: Aptitude, surface: Aptitude, strategy: Aptitude):
        self._aptitudes = dict(distance_aptitude=Aptitude(distance).value,
                              surface_aptitude=Aptitude(surface).value,
                              strategy_aptitude=Aptitude(strategy).value)
        return self

    def skill(self, skill: Skill, *, level: int = 1, unique: bool = False):
        if not isinstance(skill, Skill):
            raise TypeError('skill must be a Skill enum member')
        if type(level) is not int or not 1 <= level <= 6:
            raise ValueError('Skill level must be an integer from 1 to 6')
        if type(unique) is not bool:
            raise TypeError('unique must be a boolean')
        self._skills[int(skill)] = dict(skillId=str(int(skill)), level=level, isUnique=unique)
        return self

    def mood(self, mood: int):
        if type(mood) is not int or not -2 <= mood <= 2:
            raise ValueError('Mood must be an integer from -2 to 2')
        self._mood = mood
        return self

    def build(self) -> Runner:
        if self._stats is None or self._strategy is None or self._aptitudes is None:
            raise ValueError('Set stats, strategy, and aptitudes before building')
        extra = deepcopy(self._extra)
        extra.update(charaId=int(self._uma), mood=self._mood,
                     skills=deepcopy(list(self._skills.values())))
        return Runner(**self._stats, strategy=self._strategy, **self._aptitudes, extra=extra)
