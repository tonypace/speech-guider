# Reference CPPS script (Maryn & Weenink 2015; Praat PowerCepstrogram: Get CPPS)
# Units: dB (smoothed cepstral peak prominence above robust straight tilt line)
nch = Get number of channels
if nch > 1
    Convert to mono
endif
To PowerCepstrogram: 60, 0.002, 5000, 50
cpps = Get CPPS: "no", 0.02, 0.0005, 60, 330, 0.05, "Parabolic", 0.001, 0, "Straight", "Robust"
appendInfoLine: cpps
