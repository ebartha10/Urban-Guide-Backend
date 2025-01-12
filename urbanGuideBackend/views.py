import json
import math

import requests
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

from urbanGuideBackend import settings
from urbanGuideBackend.models import UserProfile, UserSchedule
from urbanGuideBackend.serializers import UserProfileSerializer, UserProfileGetSerializer


def home(request):
    return HttpResponse("<h1>Home Page</h1>")

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_view(request):
    user = request.user
    return Response({
        'message': f'Hello, {user.username}! This is a protected endpoint.',
    })

@api_view(['POST'])
def register_user(request):
    # Extract data from the request
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')

    # Input validation
    if not username or not password:
        return Response(
            {"error": "Username and password are required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    if User.objects.filter(username=username).exists():
        return Response(
            {"error": "Username already exists."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create the user
    user = User.objects.create_user(username=username, email=email, password=password)
    user.save()

    # Generate JWT tokens for the newly created user
    refresh = RefreshToken.for_user(user)
    return Response({
        "message": "User registered successfully!",
        "userid": user.id,
        "username": user.username,
        "tokens": {
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }
    }, status=status.HTTP_201_CREATED)

# Endpoint for creating a user profile (separate from account creation)
class UserProfileCreateView(generics.CreateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# Endpoint for updating an existing user profile
class UserProfileUpdateView(generics.RetrieveUpdateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.userprofile

# Keyword-to-Google-Places-type mapping
KEYWORD_MAPPING = {
    "Muzee și galerii de artă": "museum",
    "Parcuri": "park",
    "Grădini botanice": "botanical garden",
    "Grădini zoologice": "zoo",
    "Rezervații naturale": "natural feature",
    "Monumente importante": "tourist attraction",
    "Turnuri de observație": "point of interest",
    "Biserici și catedrale vechi": "church",
    "Piețe și târguri locale": "park",
    "Centrul vechi al orașului": "neighborhood",
    "Străzi pietonale cu arhitectură specifică": "street address",
    "Plaje": "beach",
    "Lacuri": "lake",
    "Drumeții montane": "mountain",
    "Cascade": "waterfall",
    "Clădiri administrative sau faimoase": "point of interest",
    "Primăria orașului": "local government office",
    "Clădiri istorice guvernamentale": "government office",
    "Biblioteci naționale": "library",
    "Piețe de flori și piețe alimentare": "shopping mall",
    "Piața centrală": "market",
    "Bazaruri alimentare": "grocery or supermarket",
    "Priveliști panoramice și puncte de observație": "panorama_points",
    "Platforme de observare iluminate": "point_of_interest",
    "Turnuri sau faruri cu vedere panoramică": "lighthouse",
    "Poduri faimoase": "bridges",
    "Piețe principale cu terase și cafenele": "cafe",
    "Străzi pietonale cu artiști de stradă și târguri nocturne": "shopping_mall",
    "Săli de operă": "opera",
    "Teatre de comedie sau drame": "movie theater",
    "Concerte de muzică live": "night club",
    "Baruri pe acoperiș cu vedere panoramică": "bar",
    "Pub-uri cu muzică live": "bar",
    "Cluburi de noapte faimoase": "night_club",
    "Casino-uri moderne": "casino",
    "Baruri cu jocuri de societate": "bar",
    "Proiecții de filme în aer liber": "movie_theater",
    "Cinematografe nocturne drive-in": "movie_theater",
    "Restaurante cu priveliște": "restaurant",
    "Terase deschise pe acoperișuri sau lângă apă": "restaurant"
}


@csrf_exempt
def get_places(request):
    import math

    if request.method == "POST":
        try:
            # Parse JSON data from the POST request
            data = json.loads(request.body)
            location = data.get('location', '40.712776,-74.005974')  # Default to NYC
            radius = data.get('radius', 5000)  # Default radius 5km
            keywords = data.get('keywords', [])  # Keywords to search for
            travel_mode = data.get('travel_mode', 'walk')  # Default travel mode: walk

            # Parse user's current location (latitude, longitude)
            user_lat, user_lng = map(float, location.split(','))

            # Map keywords to Google Places types
            place_types = [KEYWORD_MAPPING[keyword] for keyword in keywords if keyword in KEYWORD_MAPPING]

            # Construct the Google Places API URL
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'key': settings.GOOGLE_PLACES_API_KEY,
                'location': location,
                'radius': radius,
                'keyword': place_types,
            }

            # Make the API request
            response = requests.get(url, params=params)

            if response.status_code == 200:
                results = response.json().get('results', [])[:8]  # Limit to first 8 results
                itinerary = []

                # Helper function to calculate distance
                def calculate_distance(lat1, lng1, lat2, lng2):
                    # Haversine formula
                    R = 6371  # Earth's radius in km
                    dlat = math.radians(lat2 - lat1)
                    dlng = math.radians(lng2 - lng1)
                    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                    return R * c

                # Extract relevant details, including photo_reference and calculate distances
                enriched_results = []
                for place in results:
                    place_location = place.get("geometry", {}).get("location", {})
                    place_lat = place_location.get("lat")
                    place_lng = place_location.get("lng")

                    if place_lat is not None and place_lng is not None:
                        distance = calculate_distance(user_lat, user_lng, place_lat, place_lng)
                    else:
                        distance = float('inf')

                    enriched_place = {
                        "type": "venue",
                        "place_id": place.get("place_id"),
                        "name": place.get("name"),
                        "location": place_location,
                        "types": place.get("types", []),
                        "vicinity": place.get("vicinity"),
                        "rating": place.get("rating"),
                        "user_ratings_total": place.get("user_ratings_total"),
                        "distance": distance,  # Add distance
                        "start_time": None,  # To be calculated
                        "end_time": None,  # To be calculated
                        "visit_start_time": None,
                        "visit_end_time" : None
                    }

                    enriched_results.append(enriched_place)

                # Sort results by distance
                enriched_results.sort(key=lambda x: x["distance"])

                # Calculate travel times between venues using the Distance Matrix API
                for i in range(len(enriched_results) - 1):
                    origin = enriched_results[i]["location"]
                    destination = enriched_results[i + 1]["location"]

                    # Call Distance Matrix API
                    distance_matrix_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
                    distance_matrix_params = {
                        'origins': f'{origin["lat"]},{origin["lng"]}',
                        'destinations': f'{destination["lat"]},{destination["lng"]}',
                        'mode': travel_mode,
                        'key': settings.GOOGLE_PLACES_API_KEY,
                    }
                    dm_response = requests.get(distance_matrix_url, params=distance_matrix_params)

                    travel_time = "Unknown"
                    if dm_response.status_code == 200:
                        dm_result = dm_response.json()
                        travel_time = dm_result['rows'][0]['elements'][0].get('duration', {}).get('text', 'Unknown')

                    # Add venue
                    itinerary.append(enriched_results[i])

                    # Add travel
                    itinerary.append({
                        "type": "travel",
                        "from": enriched_results[i]["name"],
                        "to": enriched_results[i + 1]["name"],
                        "travel_mode": travel_mode,
                        "travel_time": travel_time,
                    })

                # Add the last venue
                itinerary.append(enriched_results[-1])

                # Assign start and end times (arbitrary estimates)
                start_time = 9 * 60  # Start at 9:00 AM in minutes
                for item in itinerary:
                    if item["type"] == "venue":
                        visit_duration = 60  # Assume 1 hour per place
                        item["start_time"] = f"{start_time // 60:02d}:{start_time % 60:02d} AM"
                        end_time = start_time + visit_duration
                        item["end_time"] = f"{end_time // 60:02d}:{end_time % 60:02d} AM"
                        start_time = end_time + 30  # Add 30 minutes for travel

                return JsonResponse({'itinerary': itinerary}, safe=False)
            else:
                return JsonResponse({
                    'error': 'Failed to fetch places',
                    'status_code': response.status_code,
                    'message': response.json().get('error_message', 'Unknown error')
                }, status=response.status_code)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Invalid HTTP method'}, status=405)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_schedule(request):
    if request.method == "POST":
        try:
            user = request.user

            # Parse request data
            data = json.loads(request.body)
            schedule = data.get("schedule")
            title = data.get("title", "My Trip")
            # Mark all existing schedules as inactive
            UserSchedule.objects.filter(user=user).update(is_active=False)

            # Create a new active schedule
            new_schedule = UserSchedule.objects.create(
                user=user,
                title=title,
                schedule=schedule,
                is_active=True,
            )

            return JsonResponse({
                "message": "Schedule created successfully",
                "schedule_id": str(new_schedule.schedule_id),
            }, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Invalid HTTP method"}, status=405)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_schedule(request):
    if request.method == "GET":
        try:
            user = request.user

            # Get the active schedule
            active_schedule = UserSchedule.objects.filter(user=user, is_active=True).first()
            if not active_schedule:
                return JsonResponse({"error": "No active schedule found"}, status=404)

            return JsonResponse({
                "schedule_id": str(active_schedule.schedule_id),
                "schedule": active_schedule.schedule,
                "visited_venues": active_schedule.visited_venues,
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Invalid HTTP method"}, status=405)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_next_venue(request):
    """
    Returns the first unvisited venue or the first venue being visited.
    """
    if request.method == "GET":
        try:
            # Authenticate user using JWT token
            user = request.user

            # Retrieve the active schedule for the user
            active_schedule = UserSchedule.objects.filter(user=user, is_active=True).first()
            if not active_schedule:
                return JsonResponse({"error": "No active schedule found"}, status=404)

            # Iterate over the itinerary to find the next venue
            for item in active_schedule.schedule:
                if item["type"] == "venue":
                    # Check if the venue is being visited
                    if item["visit_start_time"] and not item["visit_end_time"]:
                        return JsonResponse({"next_venue": item, "schedule_id" : active_schedule.schedule_id}, status=200)

                    # Check if the venue is unvisited
                    if not item["visit_start_time"] and not item["visit_end_time"]:
                        return JsonResponse({"next_venue": item, "schedule_id" : active_schedule.schedule_id}, status=200)

            # If all venues are visited
            return JsonResponse({"message": "All venues have been visited."}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Invalid HTTP method"}, status=405)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_visit(request):
    if request.method == "POST":
        try:
            user = request.user

            # Parse request data
            data = json.loads(request.body)
            venue_name = data.get("venue_name")
            start_time = data.get("start_time", timezone.now())
            schedule_id = data.get("schedule_id")

            # Get the schedule (active or by ID)
            schedule = UserSchedule.objects.filter(
                user=user,
                schedule_id=schedule_id if schedule_id else None,
            ).first()

            if not schedule:
                return JsonResponse({"error": "No schedule found"}, status=404)

            # Update the visit start time for the venue
            for item in schedule.schedule:
                if item["type"] == "venue" and item["name"] == venue_name:
                    item["visit_start_time"] = start_time
                    break

            schedule.save()
            return JsonResponse({"message": "Visit started successfully"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Invalid HTTP method"}, status=405)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def end_visit(request):
    if request.method == "POST":
        try:
            user = request.user

            # Parse request data
            data = json.loads(request.body)
            venue_name = data.get("venue_name")
            end_time = data.get("end_time", timezone.now())
            schedule_id = data.get("schedule_id")

            # Get the schedule (active or by ID)
            schedule = UserSchedule.objects.filter(
                user=user,
                schedule_id=schedule_id if schedule_id else None,
            ).first()

            if not schedule:
                return JsonResponse({"error": "No schedule found"}, status=404)

            # Update the visit start time for the venue
            for item in schedule.schedule:
                if item["type"] == "venue" and item["name"] == venue_name:
                    item["visit_end_time"] = end_time
                    break

            schedule.save()
            return JsonResponse({"message": "Visit ended successfully"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Invalid HTTP method"}, status=405)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_schedule_history(request):
    if request.method == "GET":
        try:
            user = request.user

            # Retrieve all schedules for the user
            schedules = UserSchedule.objects.filter(user=user).values('title', 'is_active', 'created_at', 'schedule')

            return JsonResponse(list(schedules), safe=False, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Invalid HTTP method"}, status=405)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    try:
        user = request.user
        data = {
            'username' : user.username,
            'email' : user.email,
        }
        return JsonResponse(data, safe=False, status=200)
    except UserProfile.DoesNotExist:
        return Response(
            {"error": "Profile not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_place_details(request, place_id):
    try:
        
        # Get detailed place information
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            'place_id': place_id,
            'fields': 'name,formatted_address,formatted_phone_number,rating,reviews,photos,editorial_summary,url,website,opening_hours,price_level',
            'key': settings.GOOGLE_PLACES_API_KEY
        }
        
        details_response = requests.get(details_url, params=details_params)
        
        if details_response.status_code != 200:
            return Response({
                'error': 'Failed to fetch place details',
                'status_code': details_response.status_code
            }, status=details_response.status_code)

        place_details = details_response.json().get('result', {})

        # Get up to 5 photos
        photo_urls = []
        photos = place_details.get("photos", [])[:5]  # Limit to 5 photos
        for photo in photos:
            photo_reference = photo.get("photo_reference")
            if photo_reference:
                photo_url = (
                    f"https://maps.googleapis.com/maps/api/place/photo"
                    f"?maxwidth=800&photo_reference={photo_reference}&key={settings.GOOGLE_PLACES_API_KEY}"
                )
                photo_urls.append(photo_url)

        # Format the response
        formatted_details = {
            "name": place_details.get("name"),
            "formatted_address": place_details.get("formatted_address"),
            "formatted_phone_number": place_details.get("formatted_phone_number"),
            "rating": place_details.get("rating"),
            "photos": photo_urls,
            "description": place_details.get("editorial_summary", {}).get("overview"),
            "google_maps_url": place_details.get("url"),
            "website": place_details.get("website"),
            "opening_hours": place_details.get("opening_hours", {}).get("weekday_text"),
            "price_level": place_details.get("price_level"),
            "reviews": [{
                "author_name": review.get("author_name"),
                "rating": review.get("rating"),
                "text": review.get("text"),
                "time": review.get("relative_time_description")
            } for review in place_details.get("reviews", [])]
        }

        return Response(formatted_details, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )

