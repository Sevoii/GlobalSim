/** Lookups over the generated catalog: display names and unique/inherited skill pairs. */
import {
  BUNDLED_SKILL_IDS, CHAMPIONS_MEETING_LABELS, ChampionsMeeting, SKILL_LABELS, Skill, TRACK_LABELS, Track,
  UMA_LABELS, Uma,
} from './catalog.js';

const has = (table: object, key: PropertyKey) => Object.prototype.hasOwnProperty.call(table, key);

let skillNames: Map<number, string> | undefined;

export function isSkill(id: unknown): id is Skill {
  return typeof id === 'number' && Number.isInteger(id) && has(SKILL_LABELS, id);
}

export function isUma(id: unknown): id is Uma {
  return typeof id === 'number' && Number.isInteger(id) && has(UMA_LABELS, id);
}

export function isTrack(id: unknown): id is Track {
  return typeof id === 'number' && Number.isInteger(id) && has(TRACK_LABELS, id);
}

export function isChampionsMeeting(id: unknown): id is ChampionsMeeting {
  return typeof id === 'string' && has(CHAMPIONS_MEETING_LABELS, id);
}

function requireSkill(id: unknown): Skill {
  if (!isSkill(id)) throw new RangeError(`Unknown skill ID: ${String(id)}`);
  return id;
}

/** The `Skill` member name for an ID, e.g. `'SHOOTING_STAR_100011'`. */
export function skillName(skill: Skill): string {
  skillNames ??= new Map(Object.entries(Skill).map(([name, id]) => [id, name]));
  return skillNames.get(requireSkill(skill))!;
}

/** Display name from uma-tools, e.g. `skillLabel(Skill.CORNER_ADEPT_CIRCLE) === 'Corner Adept ○'`. */
export function skillLabel(skill: Skill): string {
  return SKILL_LABELS[requireSkill(skill)]!;
}

/** The label, marked "(inherited)" where the catalog gives both versions the same name. */
export function skillDisplayName(skill: Skill): string {
  const label = skillLabel(skill);
  return skillIsInherited(skill) && !label.includes('(inherited)') ? `${label} (inherited)` : label;
}

/** Whether this is the inherited version of a unique (its ID with a leading 9 for the 1). */
export function skillIsInherited(skill: Skill): boolean {
  const text = String(requireSkill(skill));
  return text[0] === '9' && has(SKILL_LABELS, Number('1' + text.slice(1)));
}

/** The inherited version of a unique skill. Throws if it has none. */
export function inheritedSkill(skill: Skill): Skill {
  const text = String(requireSkill(skill));
  const id = Number('9' + text.slice(1));
  if (text[0] !== '1' || !isSkill(id)) throw new RangeError(`${skillName(skill)} has no inherited version`);
  return id;
}

/** The unique an inherited skill comes from. Throws for skills that are not inherited. */
export function uniqueSkill(skill: Skill): Skill {
  if (!skillIsInherited(skill)) throw new RangeError(`${skillName(skill)} is not an inherited skill`);
  return Number('1' + String(skill).slice(1)) as Skill;
}

/**
 * Whether the bundled data/skill_data.json defines this skill. The engine
 * silently ignores skills missing from the table a race uses.
 */
export function skillInBundledTable(skill: Skill): boolean {
  return BUNDLED_SKILL_IDS.has(requireSkill(skill));
}

export function umaLabel(uma: Uma): string {
  if (!isUma(uma)) throw new RangeError(`Unknown character ID: ${String(uma)}`);
  return UMA_LABELS[uma]!;
}

export function trackLabel(track: Track): string {
  if (!isTrack(track)) throw new RangeError(`Unknown track ID: ${String(track)}`);
  return TRACK_LABELS[track]!;
}

export function championsMeetingLabel(cm: ChampionsMeeting): string {
  if (!isChampionsMeeting(cm)) throw new RangeError(`Unknown Champions Meeting: ${String(cm)}`);
  return CHAMPIONS_MEETING_LABELS[cm]!;
}
