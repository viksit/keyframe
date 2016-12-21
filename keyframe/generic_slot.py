import slot_fill
import keyframe.dsl

class GenericSlot(slot_fill.Slot):
    def __init__(self, promptMsg=None):
        super(GenericSlot, self).__init__()
        self.promptMsg = promptMsg

    # TODO(viksit): This should be defined via the JSON spec file.
    entity = keyframe.dsl.FreeTextEntity(label="genericentity")
    required = False
    parseOriginal = False
    parseResponse = False

    def prompt(self):
        assert self.promptMsg
        return self.promptMsg
