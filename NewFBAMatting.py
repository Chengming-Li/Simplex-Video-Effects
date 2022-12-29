import torch

from carvekit.ml.wrap.fba_matting import FBAMatting
from carvekit.utils.models_utils import get_precision_autocast, cast_network
from carvekit.utils.pool_utils import batch_generator, thread_pool_processing
from carvekit.utils.image_utils import convert_image, load_image

class NewFBAMatting(FBAMatting):
    def __call__(self, images, trimaps, func):
        """
        Passes input images though neural network and returns segmentation masks as PIL.Image.Image instances

        Args:
            images: input images
            trimaps: Maps with the areas we need to refine

        Returns:
            segmentation masks as for input images, as PIL.Image.Image instances

        """

        if len(images) != len(trimaps):
            raise ValueError(
                "Len of specified arrays of images and trimaps should be equal!"
            )

        collect_masks = []
        autocast, dtype = get_precision_autocast(device=self.device, fp16=self.fp16)
        with autocast:
            cast_network(self, dtype)
            for idx_batch in batch_generator(range(len(images)), self.batch_size):
                inpt_images = thread_pool_processing(
                    lambda x: convert_image(load_image(images[x])), idx_batch
                )

                inpt_trimaps = thread_pool_processing(
                    lambda x: convert_image(load_image(trimaps[x]), mode="L"), idx_batch
                )

                inpt_img_batches = thread_pool_processing(
                    self.data_preprocessing, inpt_images
                )
                inpt_trimaps_batches = thread_pool_processing(
                    self.data_preprocessing, inpt_trimaps
                )

                inpt_img_batches_transformed = torch.vstack(
                    [i[1] for i in inpt_img_batches]
                )
                inpt_img_batches = torch.vstack([i[0] for i in inpt_img_batches])

                inpt_trimaps_transformed = torch.vstack(
                    [i[1] for i in inpt_trimaps_batches]
                )
                inpt_trimaps_batches = torch.vstack(
                    [i[0] for i in inpt_trimaps_batches]
                )

                with torch.no_grad():
                    inpt_img_batches = inpt_img_batches.to(self.device)
                    inpt_trimaps_batches = inpt_trimaps_batches.to(self.device)
                    inpt_img_batches_transformed = inpt_img_batches_transformed.to(
                        self.device
                    )
                    inpt_trimaps_transformed = inpt_trimaps_transformed.to(self.device)

                    output = super(FBAMatting, self).__call__(
                        inpt_img_batches,
                        inpt_trimaps_batches,
                        inpt_img_batches_transformed,
                        inpt_trimaps_transformed,
                    )
                    output_cpu = output.cpu()
                    del (
                        inpt_img_batches,
                        inpt_trimaps_batches,
                        inpt_img_batches_transformed,
                        inpt_trimaps_transformed,
                        output,
                    )
                masks = thread_pool_processing(
                    lambda x: self.data_postprocessing(output_cpu[x], inpt_trimaps[x]),
                    range(len(inpt_images)),
                )
                collect_masks += masks
                if func is not None:
                    func(len(collect_masks))
            return collect_masks
