# Demo design plan

Purpose: let a recruiter inspect a real unseen ECG, the detector's proposed beats, and
the classifier's successes and mistakes without uploading health information.

Palette: white #ffffff; paper blue #f2f6fa; ink #16324a; trace blue #1259a7;
failure burgundy #9c2947; grid pink #eedde2. Errors also have explicit text labels.
Type: system Segoe UI / sans-serif for controls and explanatory copy; tabular numerals
for probabilities and axes. No external font dependency.
Layout: a wide ECG paper plot is the main visual. A narrow, left-aligned selector column
sits beside a flexible trace region on desktop; controls stack above the plot on mobile.
Truth, prediction and confidence appear adjacent to the trace, followed by probabilities.
Evaluation and limitations are visible below, separate from the selected example.

```
Project title                          Source / Methods
Short explanation of held-out inspection
Recording filters | True label / prediction / error status
Recording chooser | ECG paper: trace and detected-peak markers
Record metadata   | Time-window control / probability distribution
Complete test-set result and comparison / limitations / attribution
```

Review against brief: prioritize trace inspection over a metric dashboard hero.
Use the ECG grid only where it has a plotting purpose. No animation or decorative
medical status lights. Confidence explicitly means uncalibrated model probability.
Keyboard controls, visible focus and readable text must work at mobile sizes.
