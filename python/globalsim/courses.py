"""Generated from data/course_data.json and alpha123/uma-tools; see CATALOG-SOURCES.md."""
from enum import Enum, IntEnum


class Track(IntEnum):
    CHUKYO = 10007  # Chukyo
    FUKUSHIMA = 10004  # Fukushima
    FUNABASHI = 10104  # Funabashi
    HAKODATE = 10002  # Hakodate
    HANSHIN = 10009  # Hanshin
    KAWASAKI = 10103  # Kawasaki
    KOKURA = 10010  # Kokura
    KYOTO = 10008  # Kyoto
    MORIOKA = 10105  # Morioka
    NAKAYAMA = 10005  # Nakayama
    NIIGATA = 10003  # Niigata
    OOI = 10101  # Ooi
    SAPPORO = 10001  # Sapporo
    TOKYO = 10006  # Tokyo
    TRACK_10201 = 10201  # Track 10201
    TRACK_10202 = 10202  # Track 10202
    TRACK_10203 = 10203  # Track 10203

    @property
    def label(self) -> str:
        """Display name from uma-tools."""
        return _TRACK_LABELS[self.value]


class ChampionsMeeting(Enum):
    AQUARIUS_CUP = 'aquarius_cup'  # Aquarius Cup
    AQUARIUS_CUP_2 = 'aquarius_cup_2'  # Aquarius Cup 2
    ARIES_CUP = 'aries_cup'  # Aries Cup
    CANCER_CUP = 'cancer_cup'  # Cancer Cup
    CANCER_CUP_2 = 'cancer_cup_2'  # Cancer Cup 2
    CAPRICORN_CUP = 'capricorn_cup'  # Capricorn Cup
    CAPRICORN_CUP_2 = 'capricorn_cup_2'  # Capricorn Cup 2
    GEMINI_CUP = 'gemini_cup'  # Gemini Cup
    GEMINI_CUP_2 = 'gemini_cup_2'  # Gemini Cup 2
    LEO_CUP = 'leo_cup'  # Leo Cup
    LEO_CUP_2 = 'leo_cup_2'  # Leo Cup 2
    LIBRA_CUP = 'libra_cup'  # Libra Cup
    LIBRA_CUP_2 = 'libra_cup_2'  # Libra Cup 2
    PISCES_CUP = 'pisces_cup'  # Pisces Cup
    SAGITTARIUS_CUP = 'sagittarius_cup'  # Sagittarius Cup
    SAGITTARIUS_CUP_2 = 'sagittarius_cup_2'  # Sagittarius Cup 2
    SCORPIO_CUP = 'scorpio_cup'  # Scorpio Cup
    SCORPIO_CUP_2 = 'scorpio_cup_2'  # Scorpio Cup 2
    TAURUS_CUP = 'taurus_cup'  # Taurus Cup
    TAURUS_CUP_2 = 'taurus_cup_2'  # Taurus Cup 2
    VIRGO_CUP = 'virgo_cup'  # Virgo Cup
    VIRGO_CUP_2 = 'virgo_cup_2'  # Virgo Cup 2

    @property
    def label(self) -> str:
        """Display name from uma-tools."""
        return _CHAMPIONSMEETING_LABELS[self.value]


_TRACK_LABELS = {
    10001: 'Sapporo',
    10002: 'Hakodate',
    10003: 'Niigata',
    10004: 'Fukushima',
    10005: 'Nakayama',
    10006: 'Tokyo',
    10007: 'Chukyo',
    10008: 'Kyoto',
    10009: 'Hanshin',
    10010: 'Kokura',
    10101: 'Ooi',
    10103: 'Kawasaki',
    10104: 'Funabashi',
    10105: 'Morioka',
    10201: 'Track 10201',
    10202: 'Track 10202',
    10203: 'Track 10203',
}


_CHAMPIONSMEETING_LABELS = {
    'aquarius_cup': 'Aquarius Cup',
    'aquarius_cup_2': 'Aquarius Cup 2',
    'aries_cup': 'Aries Cup',
    'cancer_cup': 'Cancer Cup',
    'cancer_cup_2': 'Cancer Cup 2',
    'capricorn_cup': 'Capricorn Cup',
    'capricorn_cup_2': 'Capricorn Cup 2',
    'gemini_cup': 'Gemini Cup',
    'gemini_cup_2': 'Gemini Cup 2',
    'leo_cup': 'Leo Cup',
    'leo_cup_2': 'Leo Cup 2',
    'libra_cup': 'Libra Cup',
    'libra_cup_2': 'Libra Cup 2',
    'pisces_cup': 'Pisces Cup',
    'sagittarius_cup': 'Sagittarius Cup',
    'sagittarius_cup_2': 'Sagittarius Cup 2',
    'scorpio_cup': 'Scorpio Cup',
    'scorpio_cup_2': 'Scorpio Cup 2',
    'taurus_cup': 'Taurus Cup',
    'taurus_cup_2': 'Taurus Cup 2',
    'virgo_cup': 'Virgo Cup',
    'virgo_cup_2': 'Virgo Cup 2',
}


# courseId: (raceTrackId, surface, distance, distanceType, course layout, turn)
_COURSES = {
    10101: (10001, 1, 1200, 1, 1, 1),
    10102: (10001, 1, 1500, 2, 1, 1),
    10103: (10001, 1, 1800, 2, 1, 1),
    10104: (10001, 1, 2000, 3, 1, 1),
    10105: (10001, 1, 2600, 4, 1, 1),
    10106: (10001, 2, 1000, 1, 1, 1),
    10107: (10001, 2, 1700, 2, 1, 1),
    10108: (10001, 2, 2400, 3, 1, 1),
    10201: (10002, 1, 1000, 1, 1, 1),
    10202: (10002, 1, 1200, 1, 1, 1),
    10203: (10002, 1, 1800, 2, 1, 1),
    10204: (10002, 1, 2000, 3, 1, 1),
    10205: (10002, 1, 2600, 4, 1, 1),
    10206: (10002, 2, 1000, 1, 1, 1),
    10207: (10002, 2, 1700, 2, 1, 1),
    10208: (10002, 2, 2400, 3, 1, 1),
    10301: (10003, 1, 1000, 1, 1, 4),
    10302: (10003, 1, 1200, 1, 2, 2),
    10303: (10003, 1, 1400, 1, 2, 2),
    10304: (10003, 1, 1600, 2, 3, 2),
    10305: (10003, 1, 1800, 2, 3, 2),
    10306: (10003, 1, 2000, 3, 2, 2),
    10307: (10003, 1, 2000, 3, 3, 2),
    10308: (10003, 1, 2200, 3, 2, 2),
    10309: (10003, 1, 2400, 3, 2, 2),
    10310: (10003, 2, 1200, 1, 1, 2),
    10311: (10003, 2, 1800, 2, 1, 2),
    10312: (10003, 2, 2500, 4, 1, 2),
    10401: (10004, 1, 1200, 1, 1, 1),
    10402: (10004, 1, 1800, 2, 1, 1),
    10403: (10004, 1, 2000, 3, 1, 1),
    10404: (10004, 1, 2600, 4, 1, 1),
    10405: (10004, 2, 1150, 1, 1, 1),
    10406: (10004, 2, 1700, 2, 1, 1),
    10407: (10004, 2, 2400, 3, 1, 1),
    10501: (10005, 1, 1200, 1, 3, 1),
    10502: (10005, 1, 1600, 2, 3, 1),
    10503: (10005, 1, 1800, 2, 2, 1),
    10504: (10005, 1, 2000, 3, 2, 1),
    10505: (10005, 1, 2200, 3, 3, 1),
    10506: (10005, 1, 2500, 4, 2, 1),
    10507: (10005, 1, 3600, 4, 2, 1),
    10508: (10005, 2, 1200, 1, 1, 1),
    10509: (10005, 2, 1800, 2, 1, 1),
    10510: (10005, 2, 2400, 3, 1, 1),
    10511: (10005, 2, 2500, 4, 1, 1),
    10601: (10006, 1, 1400, 1, 1, 2),
    10602: (10006, 1, 1600, 2, 1, 2),
    10603: (10006, 1, 1800, 2, 1, 2),
    10604: (10006, 1, 2000, 3, 1, 2),
    10605: (10006, 1, 2300, 3, 1, 2),
    10606: (10006, 1, 2400, 3, 1, 2),
    10607: (10006, 1, 2500, 4, 1, 2),
    10608: (10006, 1, 3400, 4, 1, 2),
    10609: (10006, 2, 1300, 1, 1, 2),
    10610: (10006, 2, 1400, 1, 1, 2),
    10611: (10006, 2, 1600, 2, 1, 2),
    10612: (10006, 2, 2100, 3, 1, 2),
    10613: (10006, 2, 2400, 3, 1, 2),
    10701: (10007, 1, 1200, 1, 1, 2),
    10702: (10007, 1, 1400, 1, 1, 2),
    10703: (10007, 1, 1600, 2, 1, 2),
    10704: (10007, 1, 2000, 3, 1, 2),
    10705: (10007, 1, 2200, 3, 1, 2),
    10706: (10007, 2, 1200, 1, 1, 2),
    10707: (10007, 2, 1400, 1, 1, 2),
    10708: (10007, 2, 1800, 2, 1, 2),
    10709: (10007, 2, 1900, 3, 1, 2),
    10801: (10008, 1, 1200, 1, 2, 1),
    10802: (10008, 1, 1400, 1, 2, 1),
    10803: (10008, 1, 1400, 1, 3, 1),
    10804: (10008, 1, 1600, 2, 2, 1),
    10805: (10008, 1, 1600, 2, 3, 1),
    10806: (10008, 1, 1800, 2, 3, 1),
    10807: (10008, 1, 2000, 3, 2, 1),
    10808: (10008, 1, 2200, 3, 3, 1),
    10809: (10008, 1, 2400, 3, 3, 1),
    10810: (10008, 1, 3000, 4, 3, 1),
    10811: (10008, 1, 3200, 4, 3, 1),
    10812: (10008, 2, 1200, 1, 1, 1),
    10813: (10008, 2, 1400, 1, 1, 1),
    10814: (10008, 2, 1800, 2, 1, 1),
    10815: (10008, 2, 1900, 3, 1, 1),
    10901: (10009, 1, 1200, 1, 2, 1),
    10902: (10009, 1, 1400, 1, 2, 1),
    10903: (10009, 1, 1600, 2, 3, 1),
    10904: (10009, 1, 1800, 2, 3, 1),
    10905: (10009, 1, 2000, 3, 2, 1),
    10906: (10009, 1, 2200, 3, 2, 1),
    10907: (10009, 1, 2400, 3, 3, 1),
    10908: (10009, 1, 2600, 4, 3, 1),
    10909: (10009, 1, 3000, 4, 2, 1),
    10910: (10009, 2, 1200, 1, 1, 1),
    10911: (10009, 2, 1400, 1, 1, 1),
    10912: (10009, 2, 1800, 2, 1, 1),
    10913: (10009, 2, 2000, 3, 1, 1),
    10914: (10009, 1, 3200, 4, 4, 1),
    11001: (10010, 1, 1200, 1, 1, 1),
    11002: (10010, 1, 1800, 2, 1, 1),
    11003: (10010, 1, 2000, 3, 1, 1),
    11004: (10010, 1, 2600, 4, 1, 1),
    11005: (10010, 2, 1000, 1, 1, 1),
    11006: (10010, 2, 1700, 2, 1, 1),
    11007: (10010, 2, 2400, 3, 1, 1),
    11101: (10101, 2, 1200, 1, 1, 1),
    11102: (10101, 2, 1800, 2, 1, 1),
    11103: (10101, 2, 2000, 3, 1, 1),
    11203: (10201, 1, 2400, 3, 1, 1),
    11301: (10103, 2, 1400, 1, 1, 2),
    11302: (10103, 2, 1600, 2, 1, 2),
    11303: (10103, 2, 2100, 3, 1, 2),
    11401: (10104, 2, 1000, 1, 1, 2),
    11402: (10104, 2, 1600, 2, 1, 2),
    11403: (10104, 2, 1800, 2, 1, 2),
    11404: (10104, 2, 2400, 3, 1, 2),
    11501: (10105, 2, 1200, 1, 1, 2),
    11502: (10105, 2, 1600, 2, 1, 2),
    11503: (10105, 2, 1800, 2, 1, 2),
    11504: (10105, 2, 2000, 3, 1, 2),
    11612: (10202, 1, 2000, 3, 1, 2),
    11613: (10202, 1, 1000, 1, 1, 2),
    11614: (10202, 1, 1600, 2, 1, 2),
    11615: (10202, 1, 2000, 3, 1, 2),
    11616: (10202, 1, 2400, 3, 1, 2),
    11617: (10202, 2, 1200, 1, 1, 2),
    11618: (10202, 2, 1400, 1, 1, 2),
    11619: (10202, 2, 1600, 2, 1, 2),
    11620: (10202, 2, 1800, 2, 1, 2),
    11621: (10202, 2, 2000, 3, 1, 2),
    11701: (10203, 1, 1000, 1, 1, 2),
    11702: (10203, 1, 1600, 2, 1, 2),
    11703: (10203, 1, 2200, 3, 1, 2),
    11704: (10203, 1, 2400, 3, 1, 2),
    11705: (10203, 2, 1200, 1, 1, 2),
    11706: (10203, 2, 1400, 1, 1, 2),
    11707: (10203, 2, 1600, 2, 1, 2),
    11708: (10203, 2, 1800, 2, 1, 2),
    11709: (10203, 2, 2000, 3, 1, 2),
}


# Global Champions Meeting presets (uma-tools umalator/app.tsx); conditions use
# the engine's JP-derived names, e.g. ground 'Good' is shown as Firm on Global.
# value: (date, courseId, season, ground, weather, time)
_CHAMPIONS_MEETINGS = {
    'taurus_cup': ('2025-08-21', 10606, 'Spring', 'Good', 'Sunny', 'Midday'),
    'gemini_cup': ('2025-09-11', 10811, 'Spring', 'Good', 'Sunny', 'Midday'),
    'cancer_cup': ('2025-10-07', 10602, 'Summer', 'Yielding', 'Sunny', 'Midday'),
    'leo_cup': ('2025-10-30', 10906, 'Summer', 'Good', 'Sunny', 'Midday'),
    'virgo_cup': ('2025-11-20', 10903, 'Autumn', 'Good', 'Sunny', 'Midday'),
    'libra_cup': ('2025-12-12', 10810, 'Autumn', 'Good', 'Sunny', 'Midday'),
    'scorpio_cup': ('2026-01-01', 10604, 'Autumn', 'Soft', 'Rainy', 'Midday'),
    'sagittarius_cup': ('2026-01-23', 10506, 'Winter', 'Good', 'Sunny', 'Midday'),
    'capricorn_cup': ('2026-02-13', 10701, 'Winter', 'Soft', 'Snowy', 'Midday'),
    'aquarius_cup': ('2026-03-06', 10611, 'Winter', 'Good', 'Sunny', 'Midday'),
    'pisces_cup': ('2026-03-30', 10914, 'Spring', 'Heavy', 'Rainy', 'Midday'),
    'aries_cup': ('2026-04-23', 10504, 'Spring', 'Good', 'Sunny', 'Midday'),
    'taurus_cup_2': ('2026-05-10', 10606, 'Spring', 'Good', 'Sunny', 'Midday'),
    'gemini_cup_2': ('2026-06-04', 10602, 'Spring', 'Good', 'Sunny', 'Midday'),
    'cancer_cup_2': ('2026-06-24', 10906, 'Summer', 'Yielding', 'Cloudy', 'Midday'),
    'leo_cup_2': ('2026-07-25', 10501, 'Summer', 'Good', 'Sunny', 'Midday'),
    'virgo_cup_2': ('2026-08-05', 11103, 'Autumn', 'Yielding', 'Sunny', 'Midday'),
    'libra_cup_2': ('2026-08-25', 10903, 'Autumn', 'Good', 'Cloudy', 'Midday'),
    'scorpio_cup_2': ('2026-09-15', 10808, 'Autumn', 'Good', 'Sunny', 'Midday'),
    'sagittarius_cup_2': ('2026-10-07', 10506, 'Winter', 'Yielding', 'Cloudy', 'Midday'),
    'capricorn_cup_2': ('2026-10-27', 10701, 'Winter', 'Good', 'Sunny', 'Midday'),
    'aquarius_cup_2': ('2026-11-17', 10611, 'Winter', 'Soft', 'Snowy', 'Midday'),
}
