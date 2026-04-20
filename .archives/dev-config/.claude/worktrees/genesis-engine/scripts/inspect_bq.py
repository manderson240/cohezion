import bluequbit
from dotenv import load_dotenv


load_dotenv()

try:
    bq = bluequbit.init()
    print(f"Client: {bq}")
    print(f"Dir: {dir(bq)}")

    # Check for specific methods
    for attr in dir(bq):
        if not attr.startswith("_"):
            val = getattr(bq, attr)
            if callable(val):
                print(f"Method: {attr}")
                # Try to print docstring
                if val.__doc__:
                    print(f"  Doc: {val.__doc__.splitlines()[0]}")

except Exception as e:
    print(f"Error: {e}")
