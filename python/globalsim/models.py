"""Optional typed helpers for race requests and decoded replay frames."""
from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Tuple


@dataclass
class Runner:
    speed: float
    stamina: float
    power: float
    guts: float
    wisdom: float
    strategy: str
    distance_aptitude: str
    surface_aptitude: str
    strategy_aptitude: str
    extra: Dict[str, Any] = field(default_factory=dict)

    _NAMES = {'distance_aptitude': 'distanceAptitude',
              'surface_aptitude': 'surfaceAptitude',
              'strategy_aptitude': 'strategyAptitude'}

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> 'Runner':
        names = (item.name for item in fields(cls) if item.name != 'extra')
        values = {name: value[cls._NAMES.get(name, name)] for name in names}
        names = values.keys()
        used = {cls._NAMES.get(name, name) for name in names}
        return cls(**values, extra={k: v for k, v in value.items() if k not in used})

    def to_dict(self) -> Dict[str, Any]:
        result = dict(self.extra)
        for item in fields(self):
            name = item.name
            if name == 'extra':
                continue
            result[self._NAMES.get(name, name)] = getattr(self, name)
        return result


@dataclass
class RaceRequest:
    seed: int
    course_id: int
    ground_condition: str
    weather: str
    season: str
    horses: List[Runner]
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> 'RaceRequest':
        keys = {'seed', 'courseId', 'groundCondition', 'weather', 'season', 'horses'}
        return cls(value['seed'], value['courseId'], value['groundCondition'],
                   value['weather'], value['season'],
                   [Runner.from_dict(h) for h in value['horses']],
                   {k: v for k, v in value.items() if k not in keys})

    def to_dict(self) -> Dict[str, Any]:
        result = dict(self.extra)
        result.update(seed=self.seed, courseId=self.course_id,
                      groundCondition=self.ground_condition, weather=self.weather,
                      season=self.season, horses=[h.to_dict() for h in self.horses])
        return result


@dataclass(frozen=True)
class RunnerFrame:
    position: float
    speed: float
    hp: float
    lane: float
    temptation_mode: float
    block_front_horse_index: float


@dataclass(frozen=True)
class RaceFrame:
    time: float
    horses: Tuple[RunnerFrame, ...]
