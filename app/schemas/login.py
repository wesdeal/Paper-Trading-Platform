from pydantic import BaseModel


# what server needs to validate a login before creating token 
class LoginRequest(BaseModel):
    email: str # there is no username column, users use email instead and have user ids
    password: str


class LoginResponse(BaseModel):
    user_id: str # return valid userid, or do we use account id?
    token: str
