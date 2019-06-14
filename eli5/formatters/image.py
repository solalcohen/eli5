# -*- coding: utf-8 -*-
from typing import Union, Optional, Callable

import numpy as np # type: ignore
from PIL import Image # type: ignore
import matplotlib.cm # type: ignore

from eli5.base import Explanation


def format_as_image(expl, # type: Explanation
    interpolation=Image.LANCZOS, # type: int
    colormap=matplotlib.cm.magma, # type: Callable[[np.ndarray], np.ndarray]
    alpha_limit=0.65, # type: Optional[Union[float, int]]
    ):
    # type: (...) -> Image
    """ Format a :class:`eli5.base.Explanation` object as an image.
    
    Parameters
    ----------
    interpolation: int, optional
        Interpolation ID / Pillow filter to use when resizing the image.

        # TODO: Example options are PIL.Image.BOX, ...

        Default is PIL.Image.LANCZOS. 

    colormap: object, optional
        Colormap scheme to be applied when converting the heatmap from grayscale to RGB.
        Either a colormap from matplotlib.cm, 
        or a callable that takes a rank 2 array and 
        returns the colored heatmap as a [0, 1] RGBA numpy array.

        # TODO: For example, matplotlib.cm has ... 

        Default is matplotlib.cm.magma (blue to red).

    alpha_limit: float or int, optional
        Maximum alpha (transparency / opacity) value allowed 
        for the alpha channel pixels in the RGBA heatmap image.

        Between 0.0 and 1.0.

        Useful when laying the heatmap over the original image, 
        so that the image can be seen over the heatmap.

        Default is alpha_limit=0.65.

    Returns
    -------
    overlay : object
        PIL image instance of the heatmap blended over the image.
    """
    image = expl.image
    heatmap = expl.heatmap
    
    # We first 1. colorize 2. resize
    # as opposed 1. resize 2. colorize

    heatmap = colorize(heatmap, colormap=colormap)
    # TODO: test colorize with a callable

    # make the alpha intensity correspond to the grayscale heatmap values
    # cap the intensity so that it's not too opaque when near maximum value
    # TODO: more options for controlling alpha, i.e. a callable?
    heat_values = expl.heatmap
    update_alpha(heatmap, starting_array=heat_values, alpha_limit=alpha_limit)

    heatmap = heatmap_to_rgba(heatmap)

    heatmap = resize_over(heatmap, image, interpolation=interpolation)
    overlay = overlay_heatmap(heatmap, image)
    return overlay


def heatmap_to_grayscale(heatmap):
    # type: (np.ndarray) -> Image
    """
    Convert ``heatmap``, a 2D numpy array with [0, 1] float values,
    into a grayscale PIL image.
    """
    heatmap = (heatmap*255).astype('uint8') # -> [0, 255] int
    return Image.fromarray(heatmap, 'L') # -> grayscale PIL


def heatmap_to_rgba(heatmap):
    # type: (np.ndarray) -> Image
    """
    Convert ``heatmap``, a rank 4 numpy array with [0, 1] float values,
    to an RGBA PIL image.
    """
    heatmap = (heatmap*255).astype('uint8') # -> [0, 255] int
    return Image.fromarray(heatmap, 'RGBA') # -> RGBA PIL


def resize_over(heatmap, image, interpolation):
    # type: (Image, Image, Union[None, int]) -> Image
    """ 
    Resize the ``heatmap`` image to fit over the original ``image``,
    using the specified ``interpolation`` method.

    See :func:`eli5.format_as_image` for more details on the `interpolation` parameter.
    
    Returns
    -------
    resized_image : object
        A resized PIL image.
    """
    # PIL seems to have a much nicer API for resizing than scipy (scipy.ndimage)
    # Also, scipy seems to have some interpolation problems: 
    # https://github.com/scipy/scipy/issues/8210
    spatial_dimensions = (image.height, image.width)
    heatmap = heatmap.resize(spatial_dimensions, resample=interpolation)
    return heatmap
    # TODO: resize a numpy array without converting to PIL image?


def colorize(heatmap, colormap):
    # type: (np.ndarray, Callable[[np.ndarray], np.ndarray]) -> np.ndarray
    """
    Apply ``colormap`` to a grayscale ``heatmap`` 2D numpy array. 

    See :func:`eli5.format_as_image` for more details on the ``colormap`` parameter.

    Returns
    -------
    new_heatmap : object
        An RGBA [0, 1] ndarray.
    """
    heatmap = colormap(heatmap) # -> [0, 1] RGBA ndarray
    return heatmap


def update_alpha(image_array, starting_array=None, alpha_limit=None):
    # type: (np.ndarray, Optional[np.ndarray], Optional[Union[float, int]]) -> None
    """
    Update the alpha channel values of an RGBA ndarray ``image_array``,
    optionally creating the alpha channel from ``starting_array``
    and setting upper limit for alpha values (opacity) to ``alpha_limit``.

    See :func:`eli5.format_as_image` and :func:`cap_alpha` 
    for more details on the ``alpha_limit`` parameter.
    
    This function modifies ``image_array`` in-place.
    """
    # get the alpha channel slice
    if isinstance(starting_array, np.ndarray):
        alpha = starting_array
    else:
        # take the alpha channel as is
        alpha = image_array[:,:,3]
    # set maximum alpha value
    alpha = cap_alpha(alpha, alpha_limit)
    # update alpha channel in the original image
    image_array[:,:,3] = alpha
    # TODO: optimisation?


def cap_alpha(alpha_arr, alpha_limit):
    # type: (np.ndarray, Union[None, float, int]) -> np.ndarray
    """
    Limit the alpha values in ``alpha_arr``, 
    by setting the maximum alpha value to be ``alpha_limit``.

    Parameters
    ----------
    alpha_arr: object
        rank 2 alpha channel array, i.e. numpy.ndarray.

        Normalized to [0, 1].
    
    alpha_limit : int or float, optional
        Real between 0 and 1 for the maximum alpha value.

        If omitted, no capping is done.

    Returns
    -------
    new_alpha : object
        Array with alpha values capped, if ``alpha_limit`` is not None
    
    Notes
    -----

    Raises
        * ValueError : if ``alpha_limit`` is outside the [0, 1] interval.
        * TypeError: if ``alpha_limit`` is not float, int, or None.
    """
    if alpha_limit is None:
        return alpha_arr
    elif isinstance(alpha_limit, (float, int)):
        if 0 <= alpha_limit <= 1:
            new_alpha = np.minimum(alpha_arr, alpha_limit)
            return new_alpha
        else:
            raise ValueError('alpha_limit must be' 
                             'between 0 and 1 inclusive, got: %f' % alpha_limit)
    else:
        raise TypeError('alpha_limit must be int or float,' 
                        'got: {}'.format(alpha_limit))


def convert_image(img):
    # type: (Union[np.ndarray, Image]) -> Image
    """ 
    Convert the ``img`` numpy.ndarray or PIL.Image.Image instance to an RGBA PIL Image.
    
    Returns
    -------
    pil_image : object
        An RGBA PIL image.
    
    Notes
    -----

    Raises
        * TypeError : if ``img`` is neither a numpy.ndarray or PIL.Image.Image.
    """
    if isinstance(img, np.ndarray):
        img = Image.fromarray(img) # ndarray -> PIL image
    if isinstance(img, Image.Image):
        img = img.convert(mode='RGBA') # -> RGBA image
    else:
        raise TypeError('img must be numpy.ndarray or PIL.Image.Image'
                        'got: {}'.format(img))
    return img


def overlay_heatmap(heatmap, image):
    # type: (Image, Image) -> Image
    """
    Blend ``heatmap`` over ``image``.
    
    Returns
    -------
    overlayed_image : object
        A blended PIL image.
    """
    # normalise to same format
    heatmap = convert_image(heatmap)
    image = convert_image(image)
    # combine the two images
    # note that the order of alpha_composite arguments matters
    overlayed_image = Image.alpha_composite(image, heatmap)
    return overlayed_image