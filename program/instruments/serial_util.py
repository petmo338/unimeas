from time import sleep
import logging
from pyvisa.errors import VisaIOError
logger = logging.getLogger(__name__)


class SerialUtil:
    QUERY_DELAY = 0.05
    ID_STRING_LENGTH = 40
    NUMBER_OF_PROBES = 4
    TIMEOUT = 1000

    @classmethod
    def probe(cls, candidates, visa_resource, identifiers, command='*IDN?'):
        d = {}
        model = ''
        for instrument in candidates:
            try:
                temp_inst = visa_resource.open_resource(instrument.resource_name, timeout=cls.TIMEOUT)
            except VisaIOError:
                break
            temp_inst.query_delay = cls.QUERY_DELAY
            logger.info('Trying to probe %s with ID command %s', instrument.resource_name, command)
            for i in xrange(cls.NUMBER_OF_PROBES):
                try:
                    model = temp_inst.query(command)
                except Exception as e:
                    logger.info('Got %s for %d time', e, i + 1)
                else:
                    break
                sleep(0.1)
            temp_inst.close()
            logger.info('Found %s', model)
            if model.find(identifiers[0]) == 0 and model.find(identifiers[1]) > 0:
                d[instrument.resource_name] = model[:cls.ID_STRING_LENGTH]
        return d

    @classmethod
    def open(cls, resource_name, visa_resource, command='*IDN?', timeout=TIMEOUT):
        instrument = None
        try:
            instrument = visa_resource.open_resource(resource_name, timeout=timeout)
        except VisaIOError:
            return None
        instrument.query_delay = cls.QUERY_DELAY
        for i in xrange(cls.NUMBER_OF_PROBES):
            try:
                instrument.query(command)
            except Exception as e:
                logger.info('Got %s for %d time', e, i + 1)
            else:
                return instrument
            sleep(0.1)
        return None
