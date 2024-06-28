from db.supabase import create_supabase_client
import json
import os

# Create the Supabase client
def create_json():
    supabase = create_supabase_client()

    # Execute the RPC call to get the schema information
    res = supabase.rpc("get_schema_json").execute()

    # Assuming res.data contains the result in the desired format
    data_to_write = res.data

    # Specify the path to the file you want to write to
    # If this script is located in the scripts/type-script-resources folder as per your structure,
    # and you want the schema.json in the same directory, use the following path
    script_dir = os.path.dirname(os.path.realpath(__file__))
    schema_file_path = os.path.join(script_dir, "schema.json")

    # Write data to schema.json
    with open(schema_file_path, "w") as file:
        json.dump(data_to_write, file, indent=4)

    # print(f"Supabase model json data has been written to {schema_file_path}")
