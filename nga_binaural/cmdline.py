import argparse
from ear.cmdline.render_file import OfflineRenderDriver, handle_strict, PeakMonitor
from ear.core import bs2051, layout
from ear.fileio import openBw64, openBw64Adm
from ear.fileio.bw64.chunks import FormatInfoChunk
from .binaural_layout import BinauralOutput
from .renderer import BinauralRenderer
from .utils import normalize_file
from itertools import chain
import sys
"""this is a modified version of render_file.py from the EAR. It was modified to adapt to the binaural rendering structure."""


def _load_binaural_output_layout(driver):
    spkr_layout = BinauralOutput()
    upmix = None
    n_channels = 2

    return spkr_layout, upmix, n_channels


def _render_input_file_binaural(driver,
                                infile,
                                spkr_layout,
                                virtual_layout,
                                upmix=None):
    """Get sample blocks of the input file after rendering.

        Parameters:
            infile (Bw64AdmReader): file to read from
            spkr_layout (Layout): layout to render to
            upmix (sparse array or None): optional upmix to apply

        Yields:
            2D sample blocks
        """
    renderer = BinauralRenderer(spkr_layout,
                                virtual_layout,
                                sr=infile.sampleRate,
                                **driver.config)
    renderer.set_rendering_items(driver.get_rendering_items(infile.adm))

    for input_samples in chain(infile.iter_sample_blocks(driver.blocksize),
                               [None]):
        if input_samples is None:
            output_samples = renderer.get_tail(infile.sampleRate,
                                               infile.channels)
        else:
            output_samples = renderer.render(infile.sampleRate, input_samples)

        output_samples *= driver.output_gain_linear

        if upmix is not None:
            output_samples *= upmix

        yield output_samples


def parse_command_line():
    parser = argparse.ArgumentParser(description="Binaural ADM renderer",
                                     conflict_handler='resolve')

    parser.add_argument("-d",
                        "--debug",
                        help="print debug information when an error occurs",
                        action="store_true")

    OfflineRenderDriver.add_args(parser)

    # supress the "target system" command line option, as this doesn't make sense for binaural
    # (target system is _always_ binaural)
    parser.add_argument("-s",
                        "--system",
                        required=False,
                        help=argparse.SUPPRESS)

    parser.add_argument("input_file")
    parser.add_argument("output_file")

    parser.add_argument("--strict",
                        help="treat unknown ADM attributes as errors",
                        action="store_true")
    args = parser.parse_args()
    return args


def render_file():
    args = parse_command_line()
    handle_strict(args)

    try:
        driver = OfflineRenderDriver(
            target_layout=args.system,
            speakers_file=None,
            output_gain_db=args.output_gain_db,
            fail_on_overload=args.fail_on_overload,
            enable_block_duration_fix=args.enable_block_duration_fix,
            programme_id=args.programme,
            complementary_object_ids=args.comp_object,
            conversion_mode=args.apply_conversion,
        )

        driver.load_output_layout = _load_binaural_output_layout
        driver.render_input_file = _render_input_file_binaural

        driver.run(args.input_file, args.output_file)

        normalize_file(args.output_file, args.output_file)

    except Exception as error:
        if args.debug:
            raise
        else:
            sys.exit(str(error))
