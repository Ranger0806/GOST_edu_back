import os
from django.conf import settings
from django.db.models import Func, F, Q
from django.db.models.fields.json import KeyTextTransform
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.utils import IntegrityError
from dotenv import load_dotenv
from yandex_gpt import YandexGPTConfigManagerForAPIKey
from yandex_gpt import YandexGPT
from google import genai
from rest_framework.parsers import MultiPartParser, FormParser
import tempfile
from .serializers import UserSerializer

load_dotenv()

config_manager = YandexGPTConfigManagerForAPIKey(
    model_type="yandexgpt-lite",
    catalog_id=os.getenv("YANDEX_FOLDER_ID"),
    api_key=os.getenv("YANDEX_API_KEY"),
)

yandex_gpt = YandexGPT(config_manager=config_manager)


class PingView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response(status=status.HTTP_200_OK)


class ApiYandexGPTView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        about = request.data.get('about')
        type = request.data.get('type')
        date_from = request.data.get('date_from')
        date_to = request.data.get('date_to')
        user_prompt = f"""Ты – помощник, который помогает студенту найти релевантные {type} по теме: '{about}'. "
                Требования по годам: 
                {f'не раньше {date_from}' if date_from else ''} 
                {'и' if (date_to and date_to) else ''}
                {f'не позже {date_to}' if date_to else ''}.
                Перечисли несколько основных источников с краткими пояснениями, почему они полезны."""
        prompt = [
            {'role': 'system', 'text': "Ты помогаешь выбирать релевантные источники информации"},
            {'role': 'user', 'text': user_prompt},
        ]
        try:
            answer = yandex_gpt.get_sync_completion(messages=prompt, temperature=0.6, max_tokens=1000,
                                                    stream=False,
                                                    completion_url='https://llm.api.cloud.yandex.net/foundationModels/v1/completion')
            return Response({"answer": answer}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"answer": 'error'}, status=status.HTTP_400_BAD_REQUEST)


class ApiGiminiQuestionsView(APIView):
    permission_classes = (AllowAny,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file = request.FILES.get('file')
        max_questions = request.data.get('max_questions', 10)
        print(max_questions)
        try:
            client = genai.Client(api_key=os.getenv("GIMINI_API"))
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(file.read())
                temp_file_path = temp_file.name
            sample_file = client.files.upload(
                file=temp_file_path,
            )
            prompt = f"Задай вопросы которые могут возьникнуть у комисии по этой презентации, важно чтобы вопросы были на русском языке, максимум {max_questions} соблюдай максимум по вопросам"
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[sample_file, prompt])
            if temp_file_path:
                os.remove(temp_file_path)
            return Response({"answer": response.text}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"answer": 'error'}, status=status.HTTP_400_BAD_REQUEST)


class RegisterUserView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        try:
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(status=status.HTTP_200_OK)
        except IntegrityError:
            return Response({"status": "error", "message": "Такой email уже зарегистрирован."},
                            status=status.HTTP_409_CONFLICT)
        return Response({"status": "error", "message": "Ошибка в данных запроса."},
                        status=status.HTTP_400_BAD_REQUEST)


class UserSigninView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response({
                "status": "error",
                "message": "Ошибка в данных запроса."
            }, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return Response(status=status.HTTP_200_OK)
        return Response({"status": "error", "message": "Неверный email или пароль."},
                        status=status.HTTP_401_UNAUTHORIZED)
