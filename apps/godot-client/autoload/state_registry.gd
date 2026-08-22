extends Node


func _init() -> void:
	# Force load all state classes to ensure class_name registration
	preload("res://state/authoritative_mirror.gd")
	preload("res://state/interaction_state.gd")
	preload("res://state/presentation_state.gd")
	preload("res://state/client_state_coordinator.gd")
	preload("res://state/presentation_state.gd")
	# ClientDebugOverlay is a Control node, not a RefCounted class, don't preload as singleton


func _ready() -> void:
	pass


func get_state_class(name: String) -> Variant:
	# Helper to get class by name for dynamic instantiation
	match name:
		"AuthoritativeMirror":
			return preload("res://state/authoritative_mirror.gd").new()
		"InteractionState":
			return preload("res://state/interaction_state.gd").new()
		"PresentationState":
			return preload("res://state/presentation_state.gd").new()
		"ClientStateCoordinator":
			return preload("res://state/client_state_coordinator.gd").new()
		_:
			return null