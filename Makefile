.EXPORT_ALL_VARIABLES:

project=mot-eggs
image_name=eu.gcr.io/terraform-admin-goauto/mot-eggs
latest_release_version := $(git describe --tags $(git rev-list --tags --max-count=1))
.PHONY: build_local_cpu, build_local_gpu, run_train, launch_training

setup_precommit:
	poetry run pre-commit install

run_tests:
	PYTHONPATH=src poetry run python -m pytest tests/

build_local_cpu:
	cd app
	docker build -t ${image_name}:${latest_release_version}-m --build-arg PROD_ENV=$(env) \
		--build-arg COMPUTE_KERNEL=cpu --build-arg IMAGE_NAME=python:3.10.4 -f Dockerfile .

build_training_gpu:
	cd trainer
	docker build -t ${image_name}-trainer:v0.0.1 --build-arg PROD_ENV=$(env) \
		--build-arg COMPUTE_KERNEL=gpu -f Dockerfile .


launch_training:
	@sed \
		-ri 's,<POSTGREST_URL>,$(POSTGREST_URL),' trainer/gcp-train-config.yaml
	@sed \
		-ri 's,<JWT_TOKEN>,$(JWT_TOKEN),' trainer/gcp-train-config.yaml
	@sed \
		-ri 's,<WANDB_API_KEY>,$(WANDB_API_KEY),' trainer/gcp-train-config.yaml
	@sed \
		-ri 's,<CONFLUENCE_API_TOKEN>,$(CONFLUENCE_API_TOKEN),' trainer/gcp-train-config.yaml


	$(eval FOLDER_COUNT=$(shell sh -c "gsutil ls gs://vertex-model-artifacts | grep -o 'mot-eggsg' | wc -l"))

	@FOLDER='gs://vertex-model-artifacts/mot-eggs-$(FOLDER_COUNT)' yq -i '.baseOutputDirectory.outputUriPrefix = strenv(FOLDER)' trainer/gcp-train-config.yaml

	 gcloud ai custom-jobs create \
	 	--region=europe-west4 \
	 	--project=ml-training-prod-goauto-1 \
	 	--display-name=mot-eggs \
	 	--config=trainer/gcp-train-config.yaml

	@echo "reverting back environment variables"

	@sed \
		-ri 's,$(POSTGREST_URL),<POSTGREST_URL>,' trainer/gcp-train-config.yaml

	@sed \
		-ri 's,$(JWT_TOKEN),<JWT_TOKEN>,' trainer/gcp-train-config.yaml

	@sed \
		-ri 's,$(WANDB_API_KEY),<WANDB_API_KEY>,' trainer/gcp-train-config.yaml

	@sed \
		-ri 's,$(CONFLUENCE_API_TOKEN),<CONFLUENCE_API_TOKEN>,' trainer/gcp-train-config.yaml


build_deepspeed:
	cd trainer
	docker build -t ${image_name}:deepspeed \
		--build-arg COMPUTE_KERNEL=gpu \
		-f Dockerfile .


# test: I have not added the correct ones here, But I think it can be used for testing triton locally for development
triton:
#  --gpus 1
	docker run \
	-it \
	-d \
	--shm-size=1g \
	--ipc=host \
	--ulimit memlock=-1 \
	--ulimit stack=67108864 \
	-p 8000:8000 -p 8001:8001 -p 8002:8002 \
	-v mot-eggs:/models \
	--name "tritonserver" \
	nvcr.io/nvidia/tritonserver:22.09-py3 \
	tritonserver \
	--model-repository=/models \
	--strict-model-config=false \
	--grpc-infer-allocation-pool-size=16 \
	--log-verbose=1


triton_sh:
	docker run \
	-it \
	-d \
	--rm \
	--gpus=all \
	--shm-size=1g \
	--ipc=host \
	--ulimit memlock=-1 \
	--ulimit stack=67108864 \
	-p 8000:8000 -p 8001:8001 -p 8002:8002 \
	-v experiments/mot-eggs:/models \
	--name "tritonserver" \
	nvcr.io/nvidia/tritonserver:22.09-py3 \
	sh

# --disable-auto-complete-config
# run: tritonserver --model-repository=/models --grpc-infer-allocation-pool-size=16 --log-verbose=1
# curl localhost:8000/v2/models/mot-eggs/config

# === Build Options ===
#   --maxBatch                  Set max batch size and build an implicit batch engine (default = 1)
#   --explicitBatch             Use explicit batch dimension when building the engine (default = explicit if ONNX model is used
#                               or if dynamic shapes are provided. Otherwise, default = implicit.)
#   --minShapes=spec            Build with dynamic shapes using a profile with the min shapes provided
#   --optShapes=spec            Build with dynamic shapes using a profile with the opt shapes provided
#   --maxShapes=spec            Build with dynamic shapes using a profile with the max shapes provided

# can take 10 minutes
convert_to_trt_trtexec:
	docker run \
	-it \
	-d \
	--gpus=all \
	--shm-size=1g \
	--ipc=host \
	--ulimit memlock=-1 \
	--ulimit stack=67108864 \
	-p 8000:8000 -p 8001:8001 -p 8002:8002 \
	-v experiments/mot-eggs:/models \
	--name "tritonserver" \
	nvcr.io/nvidia/tritonserver:22.09-py3 \
	"/usr/src/tensorrt/bin/trtexec --onnx=/models/mot-eggs/1/model.onnx --minShapes=token_type_ids:1x3,attention_mask:1x3,input_ids:1x3 --optShapes=token_type_ids:1x100,attention_mask:1x100,input_ids:1x100 --maxShapes=token_type_ids:1x400,attention_mask:1x400,input_ids:1x400 --fp16 --useCudaGraph --workspace=14000 --saveEngine=/models/mot-eggs/model.plan"

# /usr/src/tensorrt/bin/trtexec --onnx=/models/mot-eggs/1/model.onnx  --minShapes=token_type_ids:1x3,attention_mask:1x3,input_ids:1x3 --optShapes=token_type_ids:1x100,attention_mask:1x100,input_ids:1x100 --maxShapes=token_type_ids:1x400,attention_mask:1x400,input_ids:1x400 --fp16 --useCudaGraph --workspace=14000 --saveEngine=/models/mot-eggs/model.plan
# moving the model into experiments/ar-trt/mot-eggs-test
# gsutil cp -r  experiments/ar-trt/mot-eggs-test gs://kserve-models-saga-sandbox/models/ar-trt/mot-eggs-test


# Sizes are set based on the minimum being one word with start and end token, random opt, and our set max length
#  --maxBatch                  Set max batch size and build an implicit batch engine (default = 1)
#  --explicitBatch             Use explicit batch dimension when building the engine (default = explicit if ONNX model is used
#                              or if dynamic shapes are provided. Otherwise, default = implicit.)
#  --minShapes=spec            Build with dynamic shapes using a profile with the min shapes provided
#  --optShapes=spec            Build with dynamic shapes using a profile with the opt shapes provided
#  --maxShapes=spec            Build with dynamic shapes using a profile with the max shapes provided

#   --fp16                      Enable fp16 precision, in addition to fp32 (default = disabled)
#   --int8                      Enable int8 precision, in addition to fp32 (default = disabled)
#   --best                      Enable all precisions to achieve the best performance (default = disabled)


upload_to_gcs:
	gsutil -m cp -r ./mot-eggs-onnx gs://kserve-models-saga-sandbox/models

convert_to_trt:
	polygraphy convert experiments/mot-eggs/onnx-model/model.onnx -o experiments/mot-eggs/model.trt --convert-to trt  --fp16


run_train:
	docker run \
		-it \
		-d \
		--gpus all \
		-v $(PWD)/src:/app/src \
		-p 6006:6006 \
		--name $(project)-train \
		${image_name}-trainer:local \
		"poetry run deepspeed train.py --deepspeed"

run_app:
	@docker run \
		-it \
		-d \
		-p 8000:8000 \
		--name $(project)-api \
		${image_name}:v0.0.1 \
		"python gradio_app.py"


dev_container_gpu:
	@docker run \
		-it \
		-d \
		--rm \
		--gpus all \
		--name $(project)-train \
		${image_name}-trainer:v0.0.1 \
		"sleep 10000"


create_sa_key:
	gcloud iam service-accounts keys create key.json --iam-account=k8s-deploy-service-account@mot-demo-1.iam.gserviceaccount.com
	export GKE_SA_KEY=$(cat key.json | base64)