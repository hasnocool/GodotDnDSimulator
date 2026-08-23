class_name MapEntrySpawnAnchor
extends Resource

@export var anchor_id := ""
@export var area_id := ""
@export var cell := Vector2i.ZERO
@export_range(0, 3, 1) var facing_quarter := 0


func is_valid() -> bool:
    return (
        not anchor_id.strip_edges().is_empty()
        and not area_id.strip_edges().is_empty()
        and cell.x >= 0
        and cell.y >= 0
        and facing_quarter >= 0
        and facing_quarter <= 3
    )


func presentation_payload() -> Dictionary:
    return {
        "anchor_id": anchor_id,
        "area_id": area_id,
        "cell": {"x": cell.x, "y": cell.y},
        "facing_quarter": facing_quarter,
    }
