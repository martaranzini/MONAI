# Copyright 2020 MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import torch
import numpy as np
import PIL
from PIL.GifImagePlugin import Image as GifImage
from torch.utils.tensorboard import SummaryWriter
from tensorboard.compat.proto import summary_pb2
from monai.transforms.utils import rescale_array

from typing import Sequence, Union


def _image3_animated_gif(tag: str, image: Union[np.array, torch.Tensor], scale_factor: float = 1):
    """Function to actually create the animated gif.
    Args:
        tag (str): Data identifier
        image (np.array or Tensor): 3D image tensors expected to be in `HWD` format
        scale_factor (float): amount to multiply values by. if the image data is between 0 and 1, using 255 for this value will
        scale it to displayable range
    """
    assert len(image.shape) == 3, "3D image tensors expected to be in `HWD` format, len(image.shape) != 3"

    ims = [(np.asarray((image[:, :, i])) * scale_factor).astype(np.uint8) for i in range(image.shape[2])]
    ims = [GifImage.fromarray(im) for im in ims]
    img_str = b""
    for b_data in PIL.GifImagePlugin.getheader(ims[0])[0]:
        img_str += b_data
    img_str += b"\x21\xFF\x0B\x4E\x45\x54\x53\x43\x41\x50" b"\x45\x32\x2E\x30\x03\x01\x00\x00\x00"
    for i in ims:
        for b_data in PIL.GifImagePlugin.getdata(i):
            img_str += b_data
    img_str += b"\x3B"
    summary_image_str = summary_pb2.Summary.Image(height=10, width=10, colorspace=1, encoded_image_string=img_str)
    image_summary = summary_pb2.Summary.Value(tag=tag, image=summary_image_str)
    return summary_pb2.Summary(value=[image_summary])


def make_animated_gif_summary(
    tag: str,
    image: Union[np.array, torch.Tensor],
    max_out: int = 3,
    animation_axes: Sequence[int] = (3,),
    image_axes: Sequence[int] = (1, 2),
    other_indices: dict = None,
    scale_factor: float = 1,
):
    """Creates an animated gif out of an image tensor in 'CHWD' format and returns Summary.

    Args:
        tag (str): Data identifier
        image (np.array or Tensor): The image, expected to be in CHWD format
        max_out (int): maximum number of slices to animate through
        animation_axes (Sequence[int]): axis to animate on (not currently used)
        image_axes (Sequence[int]): axes of image (not currently used)
        other_indices (dict): (not currently used)
        scale_factor (float): amount to multiply values by.
            if the image data is between 0 and 1, using 255 for this value will scale it to displayable range
    """

    if max_out == 1:
        suffix = "/image"
    else:
        suffix = "/image/{}"
    if other_indices is None:
        other_indices = {}
    axis_order = [0] + list(animation_axes) + list(image_axes)

    slicing = []
    for i in range(len(image.shape)):
        if i in axis_order:
            slicing.append(slice(None))
        else:
            other_ind = other_indices.get(i, 0)
            slicing.append(slice(other_ind, other_ind + 1))
    image = image[tuple(slicing)]

    for it_i in range(min(max_out, list(image.shape)[0])):
        one_channel_img: Union[torch.Tensor, np.array] = image[it_i, :, :, :].squeeze(dim=0) if torch.is_tensor(
            image
        ) else image[it_i, :, :, :]
        summary_op = _image3_animated_gif(tag + suffix.format(it_i), one_channel_img, scale_factor)
    return summary_op


def add_animated_gif(
    writer: SummaryWriter,
    tag: str,
    image_tensor: Union[np.array, torch.Tensor],
    max_out: int,
    scale_factor: float,
    global_step: int = None,
):
    """Creates an animated gif out of an image tensor in 'CHWD' format and writes it with SummaryWriter.

    Args:
        writer (SummaryWriter): Tensorboard SummaryWriter to write to
        tag (str): Data identifier
        image_tensor (np.array or Tensor): tensor for the image to add, expected to be in CHWD format
        max_out (int): maximum number of slices to animate through
        scale_factor (float): amount to multiply values by. If the image data is between 0 and 1, using 255 for this value will
            scale it to displayable range
        global_step (int): Global step value to record
    """
    writer._get_file_writer().add_summary(
        make_animated_gif_summary(
            tag, image_tensor, max_out=max_out, animation_axes=[1], image_axes=[2, 3], scale_factor=scale_factor
        ),
        global_step,
    )


def add_animated_gif_no_channels(
    writer: SummaryWriter,
    tag: str,
    image_tensor: Union[np.array, torch.Tensor],
    max_out: int,
    scale_factor: float,
    global_step: int = None,
):
    """Creates an animated gif out of an image tensor in 'HWD' format that does not have
    a channel dimension and writes it with SummaryWriter. This is similar to the "add_animated_gif"
    after inserting a channel dimension of 1.

    Args:
        writer (SummaryWriter): Tensorboard SummaryWriter to write to
        tag (str): Data identifier
        image_tensor (np.array or Tensor): tensor for the image to add, expected to be in CHWD format
        max_out (int): maximum number of slices to animate through
        scale_factor (float): amount to multiply values by. If the image data is between 0 and 1,
                              using 255 for this value will scale it to displayable range
        global_step (int): Global step value to record
    """
    writer._get_file_writer().add_summary(
        make_animated_gif_summary(
            tag, image_tensor, max_out=max_out, animation_axes=[1], image_axes=[1, 2], scale_factor=scale_factor,
        ),
        global_step,
    )


def plot_2d_or_3d_image(data, step, writer, index=0, max_channels=1, max_frames=64, tag="output"):
    """Plot 2D or 3D image on the TensorBoard, 3D image will be converted to GIF image.

    Note:
        Plot 3D or 2D image(with more than 3 channels) as separate images.

    Args:
        data (Tensor or np.array): target data to be plotted as image on the TensorBoard.
            The data is expected to have 'NCHW[D]' dimensions, and only plot the first in the batch.
        step (int): current step to plot in a chart.
        writer (SummaryWriter): specify TensorBoard SummaryWriter to plot the image.
        index (int): plot which element in the input data batch, default is the first element.
        max_channels (int): number of channels to plot.
        max_frames (int): number of frames for 2D-t plot.
        tag (str): tag of the plotted image on TensorBoard.
    """
    assert isinstance(writer, SummaryWriter) is True, "must provide a TensorBoard SummaryWriter."
    d = data[index]
    if torch.is_tensor(d):
        d = d.detach().cpu().numpy()

    if d.ndim == 2:
        d = rescale_array(d, 0, 1)
        dataformats = "HW"
        writer.add_image(f"{tag}_{dataformats}", d, step, dataformats=dataformats)
        return

    if d.ndim == 3:
        if d.shape[0] == 3 and max_channels == 3:  # RGB
            dataformats = "CHW"
            writer.add_image(f"{tag}_{dataformats}", d, step, dataformats=dataformats)
            return
        for j, d2 in enumerate(d[:max_channels]):
            d2 = rescale_array(d2, 0, 1)
            dataformats = "HW"
            writer.add_image(f"{tag}_{dataformats}_{j}", d2, step, dataformats=dataformats)
        return

    if d.ndim >= 4:
        spatial = d.shape[-3:]
        for j, d3 in enumerate(d.reshape([-1] + list(spatial))[:max_channels]):
            d3 = rescale_array(d3, 0, 255)
            add_animated_gif(writer, f"{tag}_HWD_{j}", d3[None], max_frames, 1.0, step)
        return
