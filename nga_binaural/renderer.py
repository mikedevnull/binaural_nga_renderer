from .binaural_wrapper import BinauralWrapper, binaural_output_options
import numpy as np
from ear.core.objectbased.renderer import ObjectRenderer
from ear.core.direct_speakers.renderer import DirectSpeakersRenderer
from ear.core.scenebased.renderer import HOARenderer
from ear.options import SubOptions, OptionsHandler
from ear.core.metadata_input import ObjectRenderingItem, DirectSpeakersRenderingItem, HOARenderingItem
from ear.core.block_aligner import BlockAligner
from ear.core.layout import Layout
from .binaural_layout import BinauralOutput

"""this is a modified version of renderer.py from the EAR. It was modified to adapt to the binaural rendering structure."""

class BinauralRenderer(object):
    """
    Parameters:
        layout (.layout.Layout): loudspeaker layout to render to

    Note: 
        This is a copy of the ear.core.Renderer classes with adaptions required
        to inject the binaural rendering wrapper (because the devs are lazy)
    """
    options = OptionsHandler(
        object_renderer_opts=SubOptions(
            handler=ObjectRenderer.options,
            description="options for object based renderer",
        ),
        direct_speakers_opts=SubOptions(
            handler=DirectSpeakersRenderer.options,
            description="options for direct speakers renderer",
        ),
        hoa_renderer_opts=SubOptions(
            handler=HOARenderer.options,
            description="options for HOA renderer",
        ),
        binaural_output_opts=SubOptions(
            handler=binaural_output_options,
            description="options for binaural output",
        ),
    )

    @options.with_defaults
    def __init__(self,
                 layout,
                 virtual_layout,
                 sr,
                 object_renderer_opts={},
                 direct_speakers_opts={},
                 hoa_renderer_opts={},
                 binaural_output_opts={}):
        self.block_aligner = BlockAligner(2)

        self._object_renderer = BinauralWrapper(
            ObjectRenderer,
            layout,
            virtual_layout,
            sr,
            renderer_opts=object_renderer_opts,
            **binaural_output_opts)

        self._direct_speakers_renderer = BinauralWrapper(
            DirectSpeakersRenderer,
            layout,
            virtual_layout,
            sr,
            renderer_opts=direct_speakers_opts,
            **binaural_output_opts)

        self._hoa_renderer = BinauralWrapper(HOARenderer,
                                             layout,
                                             virtual_layout,
                                             sr,
                                             renderer_opts=hoa_renderer_opts,
                                             **binaural_output_opts)

        self.start_sample = 0

    def set_rendering_items(self, rendering_items):
        self._object_renderer.set_rendering_items([
            item for item in rendering_items
            if isinstance(item, ObjectRenderingItem)
        ])

        self._direct_speakers_renderer.set_rendering_items([
            item for item in rendering_items
            if isinstance(item, DirectSpeakersRenderingItem)
        ])

        self._hoa_renderer.set_rendering_items([
            item for item in rendering_items
            if isinstance(item, HOARenderingItem)
        ])

        # XXX: check for unsupported types?

    def render(self, sample_rate, samples):
        """Render n samples.

        Args:
            sample_rate (int): Sample Rate.
            samples (ndarray of (n, k) floats): k channels of input audio.

        Note:
            This may return fewer output samples than input samples in order to
            compensate for processing delay; the first sample returned is
            always output sample 0. Call `get_tail` after all input audio has
            been passed to `render` to get the missing samples.

        Returns:
            ndarray of (m, l): m samples and l channels of output audio.
        """
        
        self.block_aligner.add(
            self.start_sample - self._object_renderer.overall_delay,
            self._object_renderer.render(sample_rate, self.start_sample,
                                         samples))

        self.block_aligner.add(
            self.start_sample,
            self._direct_speakers_renderer.render(sample_rate,
                                                  self.start_sample, samples))

        self.block_aligner.add(
            self.start_sample,
            self._hoa_renderer.render(sample_rate, self.start_sample, samples))

        self.start_sample += len(samples)

        return self.block_aligner.get()

    def get_tail(self, sample_rate, n_channels):
        """Get an additional block of samples that completes the output."""
        total_delay = self._object_renderer.overall_delay

        return self.render(sample_rate, np.zeros((total_delay, n_channels)))
