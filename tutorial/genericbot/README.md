~~~
(keyframe1) ~/work/keyframe/tutorial/genericbot $ env  PYTHONSTARTUP=/Users/nishant/.pythonstartup PYTHONPATH=/Users/nishant/work/keyframe python ./gbot.py kwbot.json 
> hello

	>>  ResponseElement(type=text, responseType=response, text=What is your name?, carousel=None) 

> nishant

	>>  ResponseElement(type=text, responseType=response, text=Hi nishant. I can suggest recipes., carousel=None) 

> recipe

	>>  ResponseElement(type=text, responseType=response, text=What protein do you want?, carousel=None) 


	>>  ResponseElement(type=text, responseType=response, text=Which vegetable do you want?, carousel=None) 

> carrots

	>>  ResponseElement(type=text, responseType=response, text=I will look up a recipe with protein chicken and vegetable carrots., carousel=None) 

> wow you are smart

	>>  ResponseElement(type=text, responseType=response, text=Sorry I cannot understand your question. Let me forward you to a support agent., carousel=None) 


------------------------

(keyframe1) ~/work/keyframe/tutorial/genericbot $ env  PYTHONPATH=/Users/nishant/work/keyframe python ./gbot.py sarahbot.json

> did you get my donation?

	>>  ResponseElement(type=text, responseType=response, text=Once we receive your donation, it takes up to a week to process. By two weeks, you will receive a tax receipt and confirmation letter via mail., carousel=None) 

> what is a tax receipt?

	>>  ResponseElement(type=text, responseType=response, text=What is the applicable tax year?, carousel=None) 

> 2007

	>>  ResponseElement(type=text, responseType=response, text=Which state is the tax receipt for?, carousel=None) 

> CA

	>>  ResponseElement(type=text, responseType=response, text=After we receive and process your gift, we will send you a tax receipt within a week., carousel=None) 

~~~


