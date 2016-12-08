import sys

import messages

import logging

log = logging.getLogger(__name__)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
logformat = "[%(levelname)1.1s %(asctime)s %(name)s] %(message)s"
formatter = logging.Formatter(logformat)
ch.setFormatter(formatter)
log.addHandler(ch)
log.setLevel(logging.DEBUG)
log.propagate = False


class SlotFill(object):

    def __init__(self):
        self.state = "new"
        self.oneTime = False

    def fillFrom(self, canonicalMsg, slotClasses, apiResult):
        print("fill from: ", slotClasses)
        for slotClass in slotClasses:
            slotClass.canonicalMsg = canonicalMsg
            slotClass.apiResult = apiResult
            if not slotClass.filled:
                log.info("trying to fill slot %s from within sentence", slotClass.name)
                e = apiResult.entities.entity_dict.get("builtin", {})
                if slotClass.entityType in e:
                    # TODO(viksit): this needs to change to have "text" in all entities.
                    k = "text"
                    if slotClass.entityType == "DATE":
                        k = "date"
                    tmp = [i.get(k) for i in e.get(slotClass.entityType)]

                    if len(tmp) > 0:
                        slotClass.value = tmp[0]
                        slotClass.filled = True
                        log.info("\tslot was filled in this sentence")
                        continue
                    else:
                        log.info("\tslot wasn't filled in this sentence")
                        # nothing was found
                        # we'll query the user for it.
                        pass
                else:
                    log.info("\tslot wasn't filled in this sentence")

    """
    Evaluate the given sentence to see which slots you can fill from it.
    Mark the ones that are filled
    The ones that remain unfilled are the ones that we come back to each time.
    """
    def fill(self, slotClasses, canonicalMsg, apiResult, botState, channelClient):

        if not self.onetime:
            self.fillFrom(canonicalMsg, slotClasses, apiResult)
            self.onetime = True

        # Now, whats left unfilled are slots that weren't completed by the user
        # in the first go. Ask the user for input here.
        for slotClass in slotClasses:
            # TODO(viksit): add validation step here as well.
            if not slotClass.filled:
                slotClass.canonicalMsg = canonicalMsg
                slotClass.apiResult = apiResult
                log.info(">> trying to fill slot %s via user", slotClass.name)
                log.info(">> self.state: %s", self.state)
                #log.info("state: ", self.state)
                if self.state == "new":
                    # We are going to ask user for an input
                    responseType = messages.ResponseElement.RESPONSE_TYPE_RESPONSE
                    cr = messages.createTextResponse(
                        canonicalMsg,
                        slotClass.prompt(),
                        responseType)
                    channelClient.sendResponse(cr)
                    log.info("Sending response %s", cr)
                    self.state = "process_slot"
                    botState["slotClasses"] = slotClasses
                    return False

                # Finalize the slot
                elif self.state == "process_slot":
                    # We will evaluate the user's input

                    # TODO(viksit): this fillFrom function should refactor to slotClass.fill()
                    # This function could then be overwritten by a keyframe user

                    self.fillFrom(canonicalMsg, slotClasses, apiResult)
                    slotClass.validate()
                    self.state = "new"
                    botState["slotClasses"] = slotClasses
                    # continue to the next slot

        ######################################
        # End slot filling
        # Now, all slots for this should be filled.
        # check
        allFilled = True
        for slotClass in slotClasses:
            if not slotClass.filled:
                allFilled = False
                break
        self.state = "new"
        #log.info("all filled is : ", allFilled)
        return allFilled



"""
        when an utterance comes in, we send it to our API to get an intent response back.
        once the intent is known, we determine whether it contains any slots.
        we then give this to the slot processor (its a list of slot items)
        the slot processor is the first thing that is run after we get the intent.
        once the slots are filled we should make them available as a dictionary locally.

        actionObject.slots = {
          "person": {
            "filled": false/true,
            "value": "foo",
            "entity_type": ENTITY_TYPE,
            "required": true/false,
            "validated": true/false
          }, ..
        }


        before we handle the intent, slots need to be filled.

        for slotclass in slotlist:
          channel.send(slotclass.prompt())
          slotValue = slotclass.get()
          v = slotclass.validate(slotValue)
          if v:
            continue
          else:
            ask again (max tries of 3)

        once we assert that all slots are filled, we run the process and give it slot information.

"""
