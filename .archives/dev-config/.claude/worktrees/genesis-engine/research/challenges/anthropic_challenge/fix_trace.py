filename = "trace.json"
with open(filename, "r") as f:
    content = f.read()

# Replace trailing comma before closing bracket
# The file likely ends with ",\n]"
if content.strip().endswith(",\n]"):
    fixed_content = content.replace(",\n]", "\n]")
elif content.strip().endswith(",]"):
    fixed_content = content.replace(",]", "]")
else:
    # Try generic search from end
    last_comma = content.rfind(",")
    last_bracket = content.rfind("]")
    if last_comma != -1 and last_bracket != -1 and last_comma < last_bracket:
        # Check if only whitespace between
        middle = content[last_comma + 1 : last_bracket]
        if middle.strip() == "":
            fixed_content = content[:last_comma] + middle + content[last_bracket:]
        else:
            print("No trailing comma found or complex structure.")
            fixed_content = content
    else:
        fixed_content = content

with open(filename, "w") as f:
    f.write(fixed_content)
print("Fixed trace.json")
