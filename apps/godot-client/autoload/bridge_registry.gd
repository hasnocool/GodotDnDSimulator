extends Node


func _init() -> void:
	# Force load all bridge classes to ensure class_name registration
	preload("res://bridge/bridge_protocol.gd")
	preload("res://bridge/engine_transport.gd")
	preload("res://bridge/fake_engine_transport.gd")
	preload("res://bridge/tcp_json_transport.gd")
	preload("res://bridge/engine_bridge.gd")


func _ready() -> void:
	pass