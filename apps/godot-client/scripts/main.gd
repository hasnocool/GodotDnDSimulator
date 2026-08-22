# apps/godot-client/scripts/main.gd
extends Node3D


func _ready() -> void:
    # Presentation bootstrap only. The authoritative simulation will be reached through
    # a typed engine bridge in a later milestone; no rules state belongs in this scene.
    print("GodotDnDSimulator presentation scaffold ready")
