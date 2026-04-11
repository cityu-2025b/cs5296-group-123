import json
from pathlib import Path
from typing import Any

from grok_image_describer import run_pipeline


def describe_route(payload: dict[str, Any]) -> dict[str, Any]:
    path_value = payload.get("path")
    image = payload.get("image")
    run_all = bool(payload.get("run_all", False))
    image_input = payload.get("image_input")
    image_output = payload.get("image_output")
    model = payload.get("model")
    detail = payload.get("detail")

    # If path is provided, auto-detect file vs directory.
    if path_value:
        path = Path(path_value)
        if path.is_dir():
            result = run_pipeline(
                run_all=True if payload.get("run_all") is None else run_all,
                image_input=str(path),
                image_output=image_output,
                model=model,
                detail=detail,
            )
            return {"ok": True, **result}
        if path.is_file():
            result = run_pipeline(
                image=str(path),
                run_all=False,
                image_input=str(path.parent),
                image_output=image_output,
                model=model,
                detail=detail,
            )
            return {"ok": True, **result}
        return {"ok": False, "error": "Provided 'path' does not exist"}

    # If image is provided, process a single file name or file path.
    if image:
        result = run_pipeline(
            image=str(image),
            run_all=False,
            image_input=image_input,
            image_output=image_output,
            model=model,
            detail=detail,
        )
        return {"ok": True, **result}

    # If requested, process all images from the configured or provided input directory.
    if run_all:
        result = run_pipeline(
            run_all=True,
            image_input=image_input,
            image_output=image_output,
            model=model,
            detail=detail,
        )
        return {"ok": True, **result}

    return {
        "ok": False,
        "error": "Provide one of: path (file/dir), image (name/path), or run_all=true",
    }


def _demo() -> None:
    
    print("Demo: process one image by name")
    one = describe_route({"image": "Acura_005.jpg"})
    print(json.dumps(one, indent=2, ensure_ascii=False))

    print("\nDemo: process one image by full file path")
    one_path = describe_route({"path": "./image/Acura_006.jpg"})
    print(json.dumps(one_path, indent=2, ensure_ascii=False))

    print("\nDemo: process all images from a directory path")
    all_result = describe_route({"path": "./image"})
    print(json.dumps(all_result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _demo()
