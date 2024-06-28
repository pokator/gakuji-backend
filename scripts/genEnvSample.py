import os

script_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(script_path)
print(os.getcwd())
with open("../.env", "r") as infile, open("../.env.example", "w") as outfile:
    delimiter = "="
    for lines in infile:
        lines = [element + delimiter for element in lines.split(delimiter) if element][
            0
        ]
        outfile.write(lines + "\n")
# TODO: update lambda env vars as well
