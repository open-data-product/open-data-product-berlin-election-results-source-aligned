from config.data_transformation_gold_loader import DataTransformation
from tracking_decorator import TrackingDecorator
import os
import pandas as pd

@TrackingDecorator.track_time
def aggregate_data(
    data_transformation: DataTransformation,
    source_path,
    results_path,
    clean=False,
    quiet=False,
):
    already_exists, converted, empty, exception = 0, 0, 0, 0

    for input_port in data_transformation.input_ports or []:
        for file in input_port.files or []:
            source_file_path = os.path.join(
                source_path, input_port.id, file.source_file_name
            )
            target_file_path = os.path.join(results_path, input_port.id, file.target_file_name)

            if not clean and os.path.exists(target_file_path):
                if not quiet:
                    already_exists += 1
                    print(f"✓ Already exists {file.target_file_name}")
                continue

            try:
                dataframe = read_csv_file(source_file_path)

                # Apply filter
                dataframe = dataframe.filter(items=[name.name for name in file.names if name.type == "keep"])

                # Apply concatenation
                for name in [name for name in file.names if name.type == "concatenation"]:
                    dataframe[name.name] = dataframe[name.concat].agg("".join, axis=1)
                    dataframe.insert(0, name.name, dataframe.pop(name.name))

                # Apply fraction
                for name in [name for name in file.names if name.type == "fraction"]:
                    dataframe[name.name] = dataframe[name.numerator].astype(float).divide(dataframe[name.denominator].astype(float)).fillna(0)

                if dataframe.shape[0] > 0:
                    os.makedirs(
                        os.path.join(results_path, input_port.id), exist_ok=True
                    )
                    dataframe.to_csv(target_file_path, index=False)
                    converted += 1

                    if not quiet:
                        print(f"✓ Convert {os.path.basename(target_file_path)}")
                else:
                    empty += 1

                    if not quiet:
                        print(f"✗️ Empty {os.path.basename(target_file_path)}")
            except Exception as e:
                exception += 1
                print(f"✗️ Exception: {str(e)}")
    print(
        f"aggregate_data finished with already_exists: {already_exists}, converted: {converted}, empty: {empty}, exception: {exception}"
    )


#
# Helpers
#

def read_csv_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as csv_file:
            return pd.read_csv(csv_file, dtype=str)
    else:
        return None