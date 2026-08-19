class_name ProceduralAudio
extends Node


const MIX_RATE := 22050

var _ambient: AudioStreamPlayer
var _environment: AudioStreamPlayer
var _breathing: AudioStreamPlayer
var _cue: AudioStreamPlayer
var _volume := 0.65
var _muted := false
var _scene_signature := ""


func _ready() -> void:
	# Headless test/export scans have no audible output and may terminate before
	# the dummy audio thread releases generated WAV playbacks.
	if DisplayServer.get_name() == "headless":
		return
	_ambient = AudioStreamPlayer.new()
	_ambient.name = "RadioAmbience"
	add_child(_ambient)
	_environment = AudioStreamPlayer.new()
	_environment.name = "RoomEnvironment"
	add_child(_environment)
	_breathing = AudioStreamPlayer.new()
	_breathing.name = "BreathingLayer"
	add_child(_breathing)
	_cue = AudioStreamPlayer.new()
	_cue.name = "InterfaceCue"
	add_child(_cue)
	_ambient.stream = _build_stream("ambient", 2.0, true)
	_apply_volume()
	_ambient.play()


func _exit_tree() -> void:
	if is_instance_valid(_ambient):
		_ambient.stop()
		_ambient.stream = null
	if is_instance_valid(_cue):
		_cue.stop()
		_cue.stream = null
	if is_instance_valid(_environment):
		_environment.stop()
		_environment.stream = null
	if is_instance_valid(_breathing):
		_breathing.stop()
		_breathing.stream = null


func configure(volume: float, muted: bool = false) -> void:
	_volume = clampf(volume, 0.0, 1.0)
	_muted = muted
	_apply_volume()


func play_cue(cue_name: String) -> void:
	if _muted or _volume <= 0.001 or not is_instance_valid(_cue):
		return
	var duration := 0.62 if cue_name in ["bypass_burn", "launch"] else 0.46 if cue_name in ["power_lock", "seal_release", "hazard", "failure"] else 0.22
	_cue.stream = _build_stream(cue_name, duration, false)
	_cue.play()


func update_scene(snapshot: Dictionary) -> void:
	if DisplayServer.get_name() == "headless" or not is_instance_valid(_environment):
		return
	var room_id := str(snapshot.get("room_id", "relay_control"))
	var resources: Dictionary = snapshot.get("resources", {}) as Dictionary
	var oxygen := int(resources.get("oxygen", 100))
	var flags: Dictionary = snapshot.get("flags", {}) as Dictionary
	var power_state := "powered" if bool(flags.get("grid_online", false)) else "damaged"
	var oxygen_band := "critical" if oxygen <= 25 else "low" if oxygen <= 50 else "stable"
	var signature := "%s:%s:%s" % [room_id, power_state, oxygen_band]
	if signature == _scene_signature:
		return
	_scene_signature = signature
	_environment.stream = _build_stream("room_%s_%s" % [room_id, power_state], 2.8, true)
	_environment.play()
	if oxygen <= 50:
		_breathing.stream = _build_stream("breathing_%s" % oxygen_band, 2.4, true)
		_breathing.play()
	else:
		_breathing.stop()
		_breathing.stream = null
	_apply_volume()


func _apply_volume() -> void:
	if not is_instance_valid(_ambient) or not is_instance_valid(_cue):
		return
	var linear := 0.0001 if _muted else maxf(_volume, 0.0001)
	_ambient.volume_db = linear_to_db(linear * 0.20)
	if is_instance_valid(_environment):
		_environment.volume_db = linear_to_db(linear * 0.16)
	if is_instance_valid(_breathing):
		_breathing.volume_db = linear_to_db(linear * 0.22)
	_cue.volume_db = linear_to_db(linear * 0.62)


func _build_stream(kind: String, duration: float, looped: bool) -> AudioStreamWAV:
	var sample_count := maxi(1, int(MIX_RATE * duration))
	var bytes := PackedByteArray()
	bytes.resize(sample_count * 2)
	var phase := 0.0
	var frequency := _cue_frequency(kind)
	for index: int in range(sample_count):
		var time := float(index) / MIX_RATE
		var envelope := 1.0 if looped else sin(PI * clampf(time / duration, 0.0, 1.0))
		phase += TAU * frequency / MIX_RATE
		var radio_noise := sin(float(index * 17 % 101)) * 0.035
		var harmonic := sin(phase * 2.03) * 0.16
		var value := (sin(phase) * 0.52 + harmonic + radio_noise) * envelope
		if kind.begins_with("room_"):
			var machinery := sin(TAU * (frequency * 0.25) * time) * 0.26
			var relay_grit := sin(float((index * 29 + index / 13) % 173)) * 0.07
			value = (machinery + relay_grit + sin(phase) * 0.12) * (0.72 + 0.18 * sin(TAU * 0.31 * time))
			if "coolant" in kind:
				value += sin(TAU * (42.0 + sin(time * 1.7) * 7.0) * time) * 0.16
			elif "power_bay" in kind:
				value += sin(TAU * 100.0 * time) * 0.13
			elif "escape_pod" in kind:
				value += sin(TAU * 55.0 * time) * 0.10
			if "damaged" in kind and fmod(time, 0.83) < 0.025:
				value += 0.32 * sin(TAU * 900.0 * time)
		elif kind.begins_with("breathing_"):
			var breath_cycle := maxf(0.0, sin(TAU * (0.32 if "critical" in kind else 0.25) * time))
			value = (radio_noise * 2.8 + sin(TAU * 72.0 * time) * 0.08) * breath_cycle
		if kind == "hazard" or kind == "failure":
			value += sin(TAU * (frequency * 0.5 + time * 130.0) * time) * envelope * 0.24
		elif kind == "success":
			value += sin(TAU * frequency * 1.5 * time) * envelope * 0.20
		elif kind == "power_lock":
			value += sin(TAU * (280.0 + time * 760.0) * time) * envelope * 0.34
		elif kind == "bypass_burn":
			value += sin(TAU * (760.0 - time * 580.0) * time) * envelope * 0.30 + radio_noise * 3.2
		elif kind == "seal_release":
			value += radio_noise * envelope * (4.0 - 2.5 * time / duration)
		elif kind == "launch":
			value += sin(TAU * (74.0 + time * 210.0) * time) * envelope * 0.36
		var sample := clampi(int(value * 15000.0), -32768, 32767)
		bytes.encode_s16(index * 2, sample)
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = MIX_RATE
	stream.stereo = false
	stream.data = bytes
	if looped:
		stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
		stream.loop_begin = 0
		stream.loop_end = sample_count
	return stream


func _cue_frequency(kind: String) -> float:
	match kind:
		"message": return 620.0
		"candidate": return 760.0
		"movement": return 180.0
		"inspection": return 420.0
		"puzzle", "success": return 880.0
		"hazard", "failure": return 118.0
		"power_lock": return 330.0
		"bypass_burn": return 190.0
		"seal_release": return 246.0
		"launch": return 92.0
		"room_relay_control_damaged": return 96.0
		"room_central_junction_damaged": return 72.0
		"room_power_bay_damaged": return 100.0
		"room_coolant_gallery_damaged": return 58.0
		"room_escape_pod_damaged": return 82.0
		_: return 300.0
