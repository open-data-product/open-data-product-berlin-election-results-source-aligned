import os
import warnings

import pandas as pd

from lib.config.data_transformation_loader import DataTransformation
from lib.tracking_decorator import TrackingDecorator

warnings.simplefilter(action="ignore", category=FutureWarning)


@TrackingDecorator.track_time
def convert_data_to_csv(
    data_transformation: DataTransformation,
    source_path,
    results_path,
    clean=False,
    quiet=False,
):
    already_exists, converted, empty, exception = 0, 0, 0, 0

    for input_port in data_transformation.input_ports or []:
        for file in input_port.files or []:
            for dataset in file.datasets or []:
                source_file_path = os.path.join(
                    source_path, input_port.id, file.target_file_name
                )
                target_file_path = os.path.join(
                    results_path, input_port.id, dataset.target_file_name
                )

                if not clean and os.path.exists(target_file_path):
                    if not quiet:
                        already_exists += 1
                        print(f"✓ Already exists {dataset.target_file_name}")
                    continue

                _, source_file_extension = os.path.splitext(source_file_path)
                engine = "openpyxl" if source_file_extension == ".xlsx" else None

                try:
                    dataframe = pd.read_excel(
                        source_file_path,
                        engine=engine,
                        sheet_name=str(dataset.sheet_name),
                        header=dataset.header,
                        names=[name.name for name in dataset.names],
                        usecols=list(
                            range(
                                dataset.skip_cols,
                                dataset.skip_cols + len(dataset.names),
                            )
                        ),
                        skiprows=dataset.skip_rows,
                    )

                    # Apply type
                    dataframe = dataframe.astype(
                        {name.name: name.type for name in dataset.names},
                        errors="ignore",
                    )

                    # Apply remove
                    dataframe = dataframe.drop(
                        [name.name for name in dataset.names if name.remove],
                        axis=1,
                        errors="ignore",
                    )

                    # Apply zfill
                    dataframe = (
                        dataframe[
                            [name.name for name in dataset.names if not name.remove]
                        ]
                        .astype(str)
                        .apply(
                            lambda col: col.str.zfill(
                                next(
                                    name.zfill if name.zfill is not None else 0
                                    for name in dataset.names
                                    if name.name == col.name
                                )
                            )
                        )
                    )

                    if dataset.head:
                        dataframe = dataframe.head(dataset.head)

                    dataframe = dataframe.dropna()

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
        f"convert_data_to_csv finished with already_exists: {already_exists}, converted: {converted}, empty: {empty}, exception: {exception}"
    )
