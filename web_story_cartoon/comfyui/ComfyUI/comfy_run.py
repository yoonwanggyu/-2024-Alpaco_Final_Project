import os
import random
import sys
from typing import Sequence, Mapping, Any, Union
import torch
import argparse



def get_value_at_index(obj: Union[Sequence, Mapping], index: int) -> Any:
    """Returns the value at the given index of a sequence or mapping.

    If the object is a sequence (like list or string), returns the value at the given index.
    If the object is a mapping (like a dictionary), returns the value at the index-th key.

    Some return a dictionary, in these cases, we look for the "results" key

    Args:
        obj (Union[Sequence, Mapping]): The object to retrieve the value from.
        index (int): The index of the value to retrieve.

    Returns:
        Any: The value at the given index.

    Raises:
        IndexError: If the index is out of bounds for the object and the object is not a mapping.
    """
    try:
        return obj[index]
    except KeyError:
        return obj["result"][index]


# def find_path(name: str, path: str = None) -> str:
#     """
#     Recursively looks at parent folders starting from the given path until it finds the given name.
#     Returns the path as a Path object if found, or None otherwise.
#     """
#     # If no path is given, use the current working directory
#     if path is None:
#         path = os.getcwd()

#     # Check if the current directory contains the name
#     if name in os.listdir(path):
#         path_name = os.path.join(path, name)
#         print(f"{name} found: {path_name}")
#         return path_name

#     # Get the parent directory
#     parent_directory = os.path.dirname(path)

#     # If the parent directory is the same as the current directory, we've reached the root and stop the search
#     if parent_directory == path:
#         return None

#     # Recursively call the function with the parent directory
#     return find_path(name, parent_directory)


# def add_comfyui_directory_to_sys_path() -> None:
#     """
#     Add 'ComfyUI' to the sys.path
#     """
#     comfyui_path = find_path("ComfyUI")
#     if comfyui_path is not None and os.path.isdir(comfyui_path):
#         sys.path.append(comfyui_path)
#         print(f"'{comfyui_path}' added to sys.path")


# def add_extra_model_paths() -> None:
#     """
#     Parse the optional extra_model_paths.yaml file and add the parsed paths to the sys.path.
#     """
#     from main import load_extra_path_config

#     extra_model_paths = find_path("extra_model_paths.yaml")

#     if extra_model_paths is not None:
#         load_extra_path_config(extra_model_paths)
#     else:
#         print("Could not find the extra_model_paths config file.")


# add_comfyui_directory_to_sys_path()
# add_extra_model_paths()


def import_custom_nodes() -> None:
    """Find all custom nodes in the custom_nodes folder and add those node objects to NODE_CLASS_MAPPINGS

    This function sets up a new asyncio event loop, initializes the PromptServer,
    creates a PromptQueue, and initializes the custom nodes.
    """
    import asyncio
    import execution
    from nodes import init_extra_nodes
    import server

    # Creating a new event loop and setting it as the default loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Creating an instance of PromptServer with the loop
    server_instance = server.PromptServer(loop)
    execution.PromptQueue(server_instance)

    # Initializing custom nodes
    init_extra_nodes()


# 노드 improt
from nodes import (
    CLIPTextEncode,
    KSampler,
    NODE_CLASS_MAPPINGS, 
    CheckpointLoaderSimple,
    SaveImage,
    EmptyLatentImage,
    VAEDecode,
)


# # prompt.txt 에서 프롬프트 내용을 가져옴 
def main():
    parser = argparse.ArgumentParser(description="Process some files.")
    
    # 여기에 원하는 인수를 추가
    parser.add_argument('--args', type=str, help='Path to the input file')
    


    args = parser.parse_args()
    with open(f"prompt_{args.args}.txt", "r") as f:
        prompt= f.readline().strip() # 긍정 프롬프트 
        negative_prompt = f.readline().strip() # 부정 프롬프트 
        
    # 부정 프롬프트는 default 지정 
    if negative_prompt == '' : 
        negative_prompt = "text, watermark, low quality, worst quality, extra hands, extra hand, japan, china ugly, extra limb, ugly eyes"

    

    print("입력된 프롬프트: ",prompt)
    print("입력된 부정 프롬프트: ",negative_prompt)
    
    
    import_custom_nodes()
    with torch.inference_mode():
        # 체크 포인트 모델 load 
        checkpointloadersimple = CheckpointLoaderSimple()
        checkpointloadersimple_4 = checkpointloadersimple.load_checkpoint(
            ckpt_name="cardosAnime_v20.safetensors"
        )

        # latent 이미지 사이즈 설정 
        emptylatentimage = EmptyLatentImage() 
        emptylatentimage_5 = emptylatentimage.generate(
            width=1080, height=720, batch_size=1
        )

        # 긍정 프롬프트 
        cliptextencode = CLIPTextEncode() # 
        cliptextencode_6 = cliptextencode.encode(
            text = "(cartoon, brown hair, one person) " + prompt,
            clip=get_value_at_index(checkpointloadersimple_4, 1),
        )

        # 부정 프롬프트
        cliptextencode_7 = cliptextencode.encode( 
            text = negative_prompt,
            clip=get_value_at_index(checkpointloadersimple_4, 1),
        )

        
        ksampler = KSampler()
        vaedecode = VAEDecode()
        saveimage = SaveImage()

        # ksampler 
        for q in range(1):
            ksampler_3 = ksampler.sample(
                seed=233387984737895,
                steps=30,
                cfg=8,
                sampler_name="euler",
                scheduler="normal",
                denoise=1,
                model=get_value_at_index(checkpointloadersimple_4, 0),
                positive=get_value_at_index(cliptextencode_6, 0),
                negative=get_value_at_index(cliptextencode_7, 0),
                latent_image=get_value_at_index(emptylatentimage_5, 0),
            )

            vaedecode_8 = vaedecode.decode(
                samples=get_value_at_index(ksampler_3, 0),
                vae=get_value_at_index(checkpointloadersimple_4, 2),
            )

            saveimage_9 = saveimage.save_images(
                filename_prefix="ComfyUI", images=get_value_at_index(vaedecode_8, 0)
            )

    with open(f"prompt_{args.args}.txt","w") as f:
        f.write(prompt+'\n')
        f.write(negative_prompt)

if __name__ == "__main__":
    main()
