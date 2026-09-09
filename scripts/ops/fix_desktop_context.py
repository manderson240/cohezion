
path = "/home/mike-anderson/.hermes/config.yaml"
with open(path) as f:
    text = f.read()

# Disable aggressive compression triggers that trip on false positive estimates
text = text.replace("compression:\n  enabled: true", "compression:\n  enabled: false")

with open(path, "w") as f:
    f.write(text)

print("Hermes auto-compression disabled.")
