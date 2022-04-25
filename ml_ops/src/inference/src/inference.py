"""
Generating inferences from pre-trained machine learning model
"""
from easyexplore.data_import_export import DataExporter, DataImporter
from typing import Tuple

import boto3
import os
import pandas as pd
import pickle


S3_INPUT_BUCKET: str = 's3://gfb-ml-ops-data-for-prediction'
S3_MODEL_BUCKET: str = 's3://gfb-ml-ops-model'
S3_OUTPUT_BUCKET: str = 's3://gfb-ml-ops-inference'
INPUT_FILE_NAME: str = 'data_for_prediction.csv'
OUTPUT_FILE_NAME: str = 'prediction.csv'
MODEL_NAME: str = 'model.p'
S3_PROCESSOR_FOLDER: str = 'processing'
PREPROCESSING_FILE_NAME: str = 'processor.json'


def _pre_processing(df: pd.DataFrame, preprocessing_template: dict) -> pd.DataFrame:
    """
    Generate features like on training process to generate predictions from the model
    """
    _data_set: dict = {}
    for feature in df.columns:
        _data_set.update({feature: df[feature].values.tolist()})
        if feature in preprocessing_template.get('one_hot').keys():
            for value in df[feature].values:
                for one_hot_feature in preprocessing_template.get('one_hot')[feature]:
                    if _data_set.get(one_hot_feature) is None:
                        _data_set.update({one_hot_feature: []})
                    if str(f'{feature}_{value}') == one_hot_feature:
                        _data_set[one_hot_feature].append(1)
                    else:
                        _data_set[one_hot_feature].append(0)
    if df.shape[0] == 1:
        return pd.DataFrame(data=_data_set, index=[0])
    return pd.DataFrame(data=_data_set)

def main():
    """
    Generate inference from pre-trained model using data set from s3 bucket
    """
    _s3_resource = boto3.resource('s3')
    _model = pickle.loads(_s3_resource.Bucket(S3_MODEL_BUCKET.split('//')[1]).Object(MODEL_NAME).get()['Body'].read())
    _s3_model_bucket_name: str = S3_MODEL_BUCKET.split('//')[1]
    _processor_file_path: str = os.path.join(S3_MODEL_BUCKET, S3_PROCESSOR_FOLDER, PREPROCESSING_FILE_NAME)
    print(f'Load processor file from S3 bucket ({_processor_file_path})')
    _processor: dict = DataImporter(file_path=_processor_file_path, as_data_frame=False, cloud='aws', bucket_name=_s3_model_bucket_name).file()
    _df_raw: pd.DataFrame = DataImporter(file_path=os.path.join(S3_INPUT_BUCKET, INPUT_FILE_NAME), use_dask=False, sep=',', cloud='aws', bucket_name=S3_INPUT_BUCKET.split('//')[1]).file()
    print('Start pre-processing ...')
    _df = _pre_processing(df=_df_raw, preprocessing_template=_processor)
    print('Generate prediction ...')
    _predictions = _model.predict(_df[_processor.get('predictors')].values)
    _df['prediction'] = _predictions
    _prediction_file_path: str = os.path.join(S3_OUTPUT_BUCKET, OUTPUT_FILE_NAME)
    print(f'Save prediction to S3 bucket ({_prediction_file_path}) ...')
    _s3_output_bucket_name: str = S3_OUTPUT_BUCKET.split('//')[1]
    DataExporter(obj=_df, file_path=_prediction_file_path, sep=',', cloud='aws', bucket_name=_s3_output_bucket_name).file()

if __name__ == '__main__':
    main()
