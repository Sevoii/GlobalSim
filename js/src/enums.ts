/** Hand-written enums, mirroring python/globalsim/builder.py and race.py. */

export const Strategy = {
  FRONT_RUNNER: 'Nige',
  PACE_CHASER: 'Senkou',
  LATE_SURGER: 'Sasi',
  END_CLOSER: 'Oikomi',
  RUNAWAY: 'Oonige',
} as const;
export type Strategy = (typeof Strategy)[keyof typeof Strategy];

export const Aptitude = { S: 'S', A: 'A', B: 'B', C: 'C', D: 'D', E: 'E', F: 'F', G: 'G' } as const;
export type Aptitude = (typeof Aptitude)[keyof typeof Aptitude];

export const Surface = { TURF: 1, DIRT: 2 } as const;
export type Surface = (typeof Surface)[keyof typeof Surface];

export const DistanceCategory = { SPRINT: 1, MILE: 2, MEDIUM: 3, LONG: 4 } as const;
export type DistanceCategory = (typeof DistanceCategory)[keyof typeof DistanceCategory];

export const Layout = { NONE: 1, INNER: 2, OUTER: 3, OUTER_TO_INNER: 4 } as const;
export type Layout = (typeof Layout)[keyof typeof Layout];

export const Turn = { RIGHT: 1, LEFT: 2, STRAIGHT: 4 } as const;
export type Turn = (typeof Turn)[keyof typeof Turn];

/**
 * Ground conditions by their Global client names. The engine uses JP-derived
 * names, so these are translated when a request is built: Global "Firm" is sent
 * as `'Good'` and Global "Good" as `'Yielding'`. (Python's `Ground` enum stores
 * the engine names as values; here the values are the Global names so that a
 * plain `'Good'` cannot silently mean Firm.)
 */
export const Ground = { FIRM: 'Firm', GOOD: 'Good', SOFT: 'Soft', HEAVY: 'Heavy' } as const;
export type Ground = (typeof Ground)[keyof typeof Ground];
/** The engine's `groundCondition` values. */
export type EngineGround = 'Good' | 'Yielding' | 'Soft' | 'Heavy';

const TO_ENGINE: Record<Ground, EngineGround> = { Firm: 'Good', Good: 'Yielding', Soft: 'Soft', Heavy: 'Heavy' };
const FROM_ENGINE: Record<EngineGround, Ground> = { Good: 'Firm', Yielding: 'Good', Soft: 'Soft', Heavy: 'Heavy' };

/** Global ground name to the engine's `groundCondition` value. */
export function groundToEngine(ground: Ground): EngineGround {
  const value = TO_ENGINE[ground];
  if (value === undefined) throw new TypeError(`Unknown ground: ${String(ground)}`);
  return value;
}

/** The engine's `groundCondition` value to the Global ground name. */
export function groundFromEngine(ground: EngineGround): Ground {
  const value = FROM_ENGINE[ground];
  if (value === undefined) throw new TypeError(`Unknown engine ground condition: ${String(ground)}`);
  return value;
}

export const Weather = { SUNNY: 'Sunny', CLOUDY: 'Cloudy', RAINY: 'Rainy', SNOWY: 'Snowy' } as const;
export type Weather = (typeof Weather)[keyof typeof Weather];

export const Season = {
  SPRING: 'Spring', SUMMER: 'Summer', AUTUMN: 'Autumn', WINTER: 'Winter', SAKURA: 'Sakura',
} as const;
export type Season = (typeof Season)[keyof typeof Season];

export const Time = { MORNING: 'Morning', MIDDAY: 'Midday', EVENING: 'Evening', NIGHT: 'Night' } as const;
export type Time = (typeof Time)[keyof typeof Time];

export const Grade = {
  G1: 'G1', G2: 'G2', G3: 'G3', OP: 'OP', PRE_OP: 'Pre-OP', MAIDEN: 'Maiden', DEBUT: 'Debut', DAILY: 'Daily',
} as const;
export type Grade = (typeof Grade)[keyof typeof Grade];

/** The member name for `value` in an enum object, or undefined. */
export function nameOf<T extends Record<string, string | number>>(members: T, value: unknown): keyof T & string | undefined {
  for (const key in members) if (members[key] === value) return key;
  return undefined;
}

/** Whether `value` is one of the enum object's values. */
export function isMember<T extends Record<string, string | number>>(members: T, value: unknown): value is T[keyof T] {
  return nameOf(members, value) !== undefined;
}

/** `'OUTER_TO_INNER'` to `'Outer To Inner'`, like Python's `name.replace('_', ' ').title()`. */
export function title(name: string): string {
  return name.toLowerCase().replace(/_/g, ' ').replace(/(^|[^a-z])([a-z])/g, (_, a: string, b: string) => a + b.toUpperCase());
}
