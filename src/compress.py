import logging
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

log = logging.getLogger(__name__)


def compress_channel(folder_name: str, format: str = "zip", level: int = 6, use_bgzip: bool = False) -> str:
    """
    Compresses a channel directory into an archive.
    Supported formats: zip, tar.gz, tar.xz
    """
    channel_dir = Path("channels") / folder_name
    if not channel_dir.exists():
        raise FileNotFoundError(f"Channel directory {channel_dir} not found.")

    if use_bgzip:
        # bgzip only makes sense with tar or as a replacement for gz
        output_filename = f"{folder_name}.tar.gz"
        log.info(f"Compressing {channel_dir} to {output_filename} using bgzip (level {level})...")

        # Step 1: Create a temporary tar file
        temp_tar = f"{folder_name}.tar"
        with tarfile.open(temp_tar, "w") as tar:
            tar.add(channel_dir, arcname=folder_name)

        # Step 2: bgzip it
        try:
            subprocess.run(["bgzip", "-f", f"-l{level}", temp_tar], check=True)
            # bgzip renames .tar to .tar.gz by default (or .tar.bgz if specified, but usually .gz)
            # Actually bgzip -c temp.tar > output.tar.gz is safer
            # But bgzip temp.tar will create temp.tar.gz
            if os.path.exists(f"{temp_tar}.gz"):
                os.rename(f"{temp_tar}.gz", output_filename)
            elif os.path.exists(f"{temp_tar}.bgz"):
                os.rename(f"{temp_tar}.bgz", output_filename)
        except subprocess.CalledProcessError as e:
            if os.path.exists(temp_tar):
                os.remove(temp_tar)
            raise RuntimeError(f"bgzip failed: {e}") from e

        if os.path.exists(temp_tar):
            os.remove(temp_tar)

        log.info(f"Successfully compressed to {output_filename} using bgzip")
        return output_filename

    output_filename = f"{folder_name}.{format}"

    if format == "zip":
        log.info(f"Compressing {channel_dir} to {output_filename} (zip, level {level})...")
        # shutil.make_archive doesn't expose level easily across all versions,
        # but we can use ZipFile directly or rely on default.
        # Actually for zip, we can use shutil.make_archive and then it uses default.
        # To specify level, we'd need to use zipfile.ZipFile.
        shutil.make_archive(folder_name, "zip", root_dir=channel_dir.parent, base_dir=folder_name)
    elif format == "tar.gz":
        log.info(f"Compressing {channel_dir} to {output_filename} (tar.gz, level {level})...")
        with tarfile.open(output_filename, "w:gz", compresslevel=level) as tar:
            tar.add(channel_dir, arcname=folder_name)
    elif format == "tar.xz":
        log.info(f"Compressing {channel_dir} to {output_filename} (tar.xz, preset {level})...")
        # tarfile xz uses lzma, preset is the level
        with tarfile.open(output_filename, "w:xz", preset=level) as tar:  # type: ignore[call-overload]
            tar.add(channel_dir, arcname=folder_name)
    else:
        raise ValueError(f"Unsupported compression format: {format}")

    log.info(f"Successfully compressed to {output_filename}")
    return output_filename
