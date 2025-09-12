Unity Channel Mask Presets (Example)

Layers
- Base (default): hands/body core motions. Avatar mask excludes face/eyes.
- Face (face): facial expressions, lips. Mask includes head/face bones only.
- Gaze (gaze): eye bones only.

Suggestions
- Base weight: 1.0; Face: 0.7–0.9; Gaze: 1.0
- Transitions: use short blend-in/out (0.05–0.1s) to avoid pops.
- Ensure states use "Foot IK" off if not needed.

Mapping
- Timeline clip ids map to Animator state names: keep IDs consistent.
- FACE_ALERT on face layer; GAZE_FORWARD on gaze layer.

