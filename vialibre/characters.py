from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class CharacterDefinition:
    id: str
    display_name: str
    idle_model: str
    run_model: str
    actor_model: Optional[str] = None
    idle_anim: str = "idle"
    run_anim: str = "run"
    scale: float = 0.4
    heading: float = 180.0
    z_offset: float = 0.0


CHARACTERS: Tuple[CharacterDefinition, ...] = (
    CharacterDefinition(
        id="alfred",
        display_name="Alfred",
        idle_model="assets/Alfred_idle.bam",
        run_model="assets/Alfred_run.bam",
        actor_model="assets/Alfred_run.bam",
        idle_anim="Armature|mixamo.com|Layer0",
        run_anim="mixamo.com",
        scale=0.522,
    ),
    CharacterDefinition(
        id="tony",
        display_name="Tony",
        idle_model="assets/Tony_idle.bam",
        run_model="assets/Tony_run.bam",
    ),
    CharacterDefinition(
        id="teresa",
        display_name="Teresa",
        idle_model="assets/Teresa_idle1.bam",
        run_model="assets/Teresa_run.bam",
        scale=0.913,
    ),
    CharacterDefinition(
        id="bob",
        display_name="Bob",
        idle_model="assets/Bob_Idle.bam",
        run_model="assets/Bob_run.bam",
        actor_model="assets/Bob_run.bam",
        idle_anim="Armature|mixamo.com|Layer0",
        run_anim="mixamo.com",
        scale=0.612,
    ),
)

CHARACTER_BY_ID: Dict[str, CharacterDefinition] = {
    character.id: character for character in CHARACTERS
}

DEFAULT_CHARACTER_ID = "tony"


def normalize_character_id(character_id) -> str:
    if character_id is None:
        return DEFAULT_CHARACTER_ID

    key = str(character_id).strip().lower()
    if key in CHARACTER_BY_ID:
        return key
    return DEFAULT_CHARACTER_ID


def get_character_definition(character_id) -> CharacterDefinition:
    return CHARACTER_BY_ID[normalize_character_id(character_id)]
