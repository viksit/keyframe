class NotFoundError(Exception):
    pass

class RequestError(Exception):
    pass


class ElasticsearchDslException(Exception):
    pass


class UnknownDslObject(ElasticsearchDslException):
    pass


class ValidationException(ValueError, ElasticsearchDslException):
    pass


class IllegalOperation(ElasticsearchDslException):
    pass
