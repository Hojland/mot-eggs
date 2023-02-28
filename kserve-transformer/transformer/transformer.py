#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import os
from pathlib import Path
from typing import Dict

import numpy as np
from google.cloud import storage
from transformers import AutoConfig, AutoTokenizer

import kserve
import tritonclient.http as httpclient

logging.basicConfig(level=logging.DEBUG)

STORAGE_URI = os.getenv(
    "CONFIG_PATH_STORAGE_URI",
    "gs://kserve-models-saga-sandbox/models/mot-eggs",
)
K8S_NAMESPACE = "models"


def softmax(_outputs):
    maxes = np.max(_outputs, axis=-1, keepdims=True)
    shifted_exp = np.exp(_outputs - maxes)
    return shifted_exp / shifted_exp.sum(axis=-1, keepdims=True)


def load_configs(model_name: str):
    bucket = STORAGE_URI.split("/")[2]
    object_name = "/".join(STORAGE_URI.split("/")[3:])

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket)
    config_blobs = [
        blob
        for blob in bucket.list_blobs(prefix=object_name)
        if "config.json" in blob.name
    ]

    configs = {}
    for config_blob in config_blobs:
        version_id = config_blob.name.split("/")[-2]
        if version_id == model_name:
            version_id = "default"

        config = json.loads(config_blob.download_as_bytes())
        configs[version_id] = config

    assert configs, "Can't find the config file for AR model"
    return configs


# this needs to work kind of like textclassificationpipeline from transformers
class SequenceTransformer(kserve.Model):
    def __init__(self, predictor_host: str, name: str = "mot-eggs"):
        super().__init__(name)
        self.predictor_host = predictor_host
        configs = load_configs(name)
        self.bert_config = configs["default"]
        tokenizer_path = self.bert_config["_name_or_path"]
        self.bert_tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_path,
        )
        self.triton_client = None

    # inputs is model_name as the first argument in the string, and then a dict with texts and then a list of texts
    def preprocess(self, inputs: Dict[str, Dict]) -> Dict:
        # inputs = {"text": "please process this po"}
        max_length: int = 400
        tokenized_inputs = self.bert_tokenizer(
            inputs["text"],
            is_split_into_words=False,
            return_offsets_mapping=False,
            padding=False,
            max_length=max_length,
            truncation=True,
            return_tensors="np",
        )
        return tokenized_inputs

    async def predict(self, tokenized_inputs: Dict) -> Dict:
        if not self.triton_client:
            self.triton_client = httpclient.InferenceServerClient(
                url=self.predictor_host, verbose=False
            )

        attention_mask = (
            tokenized_inputs["attention_mask"].reshape(
                -1, tokenized_inputs["attention_mask"].shape[-1]
            )
            # .astype(np.int32)
        )
        input_ids = (
            tokenized_inputs["input_ids"].reshape(
                -1, tokenized_inputs["input_ids"].shape[-1]
            )
            # .astype(np.int32)
        )

        inputs = [
            httpclient.InferInput(
                "attention_mask", list(attention_mask.shape), "INT64"
            ),
            httpclient.InferInput("input_ids", list(input_ids.shape), "INT64"),
        ]
        inputs[0].set_data_from_numpy(attention_mask)
        inputs[1].set_data_from_numpy(input_ids)

        outputs = [httpclient.InferRequestedOutput("logits", binary_data=False)]
        result = self.triton_client.infer("mot-eggs", inputs, outputs=outputs)
        res = result.get_response()
        return res

    def postprocess(self, res: Dict) -> Dict:
        top_k = None
        id2label = self.bert_config["id2label"]

        logits = res["outputs"][0]["data"]

        dict_scores = [
            {"label": id2label[str(i)], "score": score.item()}
            for i, score in enumerate(softmax(logits))
        ]
        dict_scores.sort(key=lambda x: x["score"], reverse=True)
        if top_k is not None:
            dict_scores = dict_scores[:top_k]

        return {"label_scores": dict_scores}

if __name__ == "__main__":
    transformer = SequenceTransformer(
        predictor_host="localhost:8000",
        name="mot-eggs",
    )
    self = transformer
    server = kserve.ModelServer()
    server.start(models=[transformer])
