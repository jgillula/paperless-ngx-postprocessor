import json
import logging
from ollama import ps, pull, chat, ProcessResponse, ChatResponse
from datetime import datetime
from pydantic import BaseModel

class AI:
    def __init__(self, model, logger = None):
        self._logger = logger
        if self._logger is None:
            logging.basicConfig(format="[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s", level="CRITICAL")
            self._logger = logging.getLogger()
        self._model = model
        self.systemprompt = 'You are a personalized document analyzer. Your task is to analyze documents and extract relevant information. \
            \
            Analyze the document content which you will get in the next message.\
            After that I will send you the instruction which information you need to extract.\
            Be Short and concise and answer without any other additional information and without control characters. \
            Correct spelling or other errors in your answer. Return the info in JSON format. '
    def getResponse(self, content, prompt):
        messages = [
        {
            'role': 'system',
            'content': self.systemprompt,
        },
        {
            'role': 'system',
            'content': content,
        },
        {
            'role': 'user',
            'content': prompt,
        },
        ]

        response = chat(self._model, messages=messages, format=info.model_json_schema())
        jsonvalue = json.loads(response['message']['content'])
        return (jsonvalue['info'])
    
    def selfCheck(self):
        start = datetime.now()
        response = pull(self._model, stream=True)
        end = datetime.now()
        duration = end-start
        self._logger.info("It took me " + str(duration) + " to pull the model")
        progress_states = set()
        try:
            for progress in response:
                if progress.get('status') in progress_states:
                    continue
        except Exception as X:
            return False
        progress_states.add(progress.get('status'))
        self._logger.info(progress.get('status'))

        self._logger.info('\n')
        start = datetime.now()
        self._logger.info('Waiting for model to load... \n')
        end = datetime.now()
        duration = end-start
        self._logger.info("It took me " + str(duration) + " to load the model")

        response: ProcessResponse = ps()
 #       for model in response.models:
 #           self._logger.info('Model: ', str(model.model))
 #           self._logger.info('  Digest: ', str(model.digest))
 #           self._logger.info('  Expires at: ', str(model.expires_at))
 #           self._logger.info('  Size: ', str(model.size))
 #           self._logger.info('  Size vram: ', str(model.size_vram))
 #           self._logger.info('  Details: ', str(model.details))
 #           self._logger.info('\n')
            
        start = datetime.now()

        response: ChatResponse = chat(model=self._model, messages=[
        {
            'role': 'user',
            'content': 'Say Hello Gemma',
        },
        ])

        self._logger.info(response['message']['content'])
        end = datetime.now()
        duration = end-start
        self._logger.info("It took me " + str(duration) + " to greet you")
        return True;

class info(BaseModel):
    info: str