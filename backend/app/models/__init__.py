# Models module
from app.models.project import Project
from app.models.character import Character
from app.models.world_setting import WorldSetting
from app.models.volume import Volume
from app.models.chapter import Chapter
from app.models.chapter_memory import ChapterMemory
from app.models.character_state import CharacterState
from app.models.foreshadow_record import ForeshadowRecord
from app.models.review_note import ReviewNote
from app.models.publish_task import PublishTask
from app.models.story_bible import StoryBible
from app.models.arc_envelope import (
    ArcEnvelope,
    ArcStructureDraft,
    ArcEnvelopeAnalysis,
    ProvisionalPromotionRecord,
)
# v2.7 新增
from app.models.chapter_rewrite_attempt import ChapterRewriteAttempt
from app.models.band_experience_plan import BandExperiencePlan
from app.models.comment import (
    AudienceHintPack,
    AudienceSignal,
    AudienceTrend,
    CommentSignal,
    CommentSignalCandidate,
    RawComment,
    SignalWindowAggregate,
)
# BookState 模型 (Phase 1)
from app.models.world_nodes import WorldNode, WorldNodeType, Importance
from app.models.world_edges import WorldEdge, EdgeType, EdgeFamily, Directionality
from app.models.graph_deltas import GraphDelta, DeltaType, SourceType, NodePatchOp, EdgePatchOp
# Phase 2: 地图系统 Scheme C
from app.models.subworld import SubWorld, SubWorldType, MapRegion
from app.models.map_nodes import MapNode, MapNodeType
from app.models.map_edges import MapEdge, MapEdgeType
# Phase 4: 人物性格系统
from app.models.personality import (
    PersonalityLoadout,
    PersonalityTraitInstance,
    PersonalityEvolution,
    TraitCategory,
    TraitType,
)

__all__ = [
    "Project",
    "Character",
    "WorldSetting",
    "Volume",
    "Chapter",
    "ChapterMemory",
    "CharacterState",
    "ForeshadowRecord",
    "ReviewNote",
    "PublishTask",
    "StoryBible",
    "ArcEnvelope",
    "ArcStructureDraft",
    "ArcEnvelopeAnalysis",
    "ProvisionalPromotionRecord",
    # v2.7
    "ChapterRewriteAttempt",
    "BandExperiencePlan",
    "AudienceHintPack",
    "AudienceSignal",
    "AudienceTrend",
    "CommentSignal",
    "CommentSignalCandidate",
    "RawComment",
    "SignalWindowAggregate",
    # BookState (Phase 1)
    "WorldNode",
    "WorldNodeType",
    "Importance",
    "WorldEdge",
    "EdgeType",
    "EdgeFamily",
    "Directionality",
    "GraphDelta",
    "DeltaType",
    "SourceType",
    "NodePatchOp",
    "EdgePatchOp",
    # Phase 2: 地图系统 Scheme C
    "SubWorld",
    "SubWorldType",
    "MapRegion",
    "MapNode",
    "MapNodeType",
    "MapEdge",
    "MapEdgeType",
    # Phase 4: 人物性格系统
    "PersonalityLoadout",
    "PersonalityTraitInstance",
    "PersonalityEvolution",
    "TraitCategory",
    "TraitType",
]
