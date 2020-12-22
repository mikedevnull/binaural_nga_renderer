from pydub import AudioSegment
from pydub.effects import normalize


def normalize_file(input_file, output_file):
    normalized_output = normalize(AudioSegment.from_file(input_file),
                                  headroom=0.3)
    normalized_output.export(output_file, format="wav")
