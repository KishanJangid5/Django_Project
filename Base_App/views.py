from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView as AuthLoginView
from Base_App.models import BookTable, AboutUs, Feedback, ItemList, Items, Cart
from django.contrib.auth import logout
from django.urls import reverse_lazy

def add_to_cart(request):
    if request.method == 'POST' and request.user.is_authenticated:
        item_id = request.POST.get('item_id')
        item = get_object_or_404(Items, id=item_id)

        print(f'Item ID: {item_id}')  # Debug print
        print(f'Item: {item.Item_name}, Price: {item.Price}')  # Debug print

        # Check if the item is already in the user's cart
        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            item=item,
            defaults={'quantity': 1}
        )
        if not created:
            cart_item.quantity += 1
            cart_item.save()

        print(f'Cart item added/updated: {cart_item}')  # Debug print

        return JsonResponse({'message': 'Item added to cart'})
    else:
        print('Invalid request')  # Debug print
        return JsonResponse({'error': 'Invalid request'}, status=400)


def get_cart_items(request):
    if request.user.is_authenticated:
        cart_items = Cart.objects.filter(user=request.user).select_related('item')
        items = [
            {
                'id': cart_item.item.id,
                'name': cart_item.item.Item_name,
                'quantity': cart_item.quantity,
                'price': cart_item.item.Price,
                'total': cart_item.quantity * cart_item.item.Price,
            }
            for cart_item in cart_items
        ]
        return JsonResponse({'items': items}, safe=False)
    return JsonResponse({'error': 'User not authenticated'}, status=401)


def update_cart(request):
    if request.method == 'POST' and request.user.is_authenticated:
        item_id = request.POST.get('item_id')
        action = request.POST.get('action')  # 'increase' or 'decrease'
        item = get_object_or_404(Items, id=item_id)
        cart_item = Cart.objects.filter(user=request.user, item=item).first()
        if cart_item:
            if action == 'increase':
                cart_item.quantity += 1
                cart_item.save()
            elif action == 'decrease':
                if cart_item.quantity > 1:
                    cart_item.quantity -= 1
                    cart_item.save()
                else:
                    cart_item.delete()
        return JsonResponse({'message': 'Cart updated'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

class LoginView(AuthLoginView):
    template_name = 'login.html'
    def get_success_url(self):
        # Check if the user is an admin
        if self.request.user.is_staff:
            return reverse_lazy('admin:index')  # Redirects to the Django admin panel
        return reverse_lazy('Home')  # Redirects to the home page if not an admin

def LogoutView(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('Home')  # Redirect to a page after logout, e.g., the home page

def SignupView(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('Home')
        else:
            messages.error(request, 'Error during signup. Please try again.')
    else:
        form = UserCreationForm()
    return render(request, 'login.html', {'form': form, 'tab': 'signup'})


def HomeView(request):
    items =  Items.objects.all()
    list = ItemList.objects.all()
    review = Feedback.objects.all().order_by('-id')[:5]
    return render(request, 'home.html',{'items': items, 'list': list, 'review': review})


def AboutView(request):
    data = AboutUs.objects.all()
    return render(request, 'about.html',{'data': data})


def MenuView(request):
    items =  Items.objects.all()
    list = ItemList.objects.all()
    return render(request, 'menu.html', {'items': items, 'list': list})


def BookTableView(request):
    # Pass the API key to the template
    google_maps_api_key = settings.GOOGLE_MAPS_API_KEY

    if request.method == 'POST':
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':  # Check if it's an AJAX request
            name = request.POST.get('user_name')
            phone_number = request.POST.get('phone_number')
            email = request.POST.get('user_email')
            total_person = request.POST.get('total_person')
            booking_data = request.POST.get('booking_data')

            # Validate the form data
            if name and len(phone_number) == 10 and email and total_person != '0' and booking_data:
                try:
                    # Save the booking data to the database
                    booking = BookTable(Name=name, Phone_number=int(phone_number),
                                         Email=email, Total_person=int(total_person),
                                         Booking_date=booking_data)
                    booking.save()

                    # Store booking ID in session for later use in checkout
                    request.session['booking_id'] = booking.id

                    # Send confirmation email (using console backend in development)
                    subject = 'Booking Confirmation'
                    message = f"Hello {name},\n\nYour booking has been successfully received.\n" \
                              f"Booking details:\nTotal persons: {total_person}\n" \
                              f"Booking date: {booking_data}\n\nThank you for choosing us!"

                    from_email = settings.DEFAULT_FROM_EMAIL
                    recipient_list = [email]  # The email of the user

                    # Send the confirmation email
                    try:
                        send_mail(subject, message, from_email, recipient_list)
                    except Exception as e:
                        # Log the error but don't fail the booking
                        print(f"Email sending failed: {e}")

                    return JsonResponse({'success': True, 'message': 'Table booked successfully! Please check your confirmation email.'})
                except Exception as e:
                    return JsonResponse({'success': False, 'message': 'An error occurred while booking the table. Please try again.'})
            else:
                return JsonResponse({'success': False, 'message': 'Please fill in all required fields correctly.'})
        else:
            # Handle non-AJAX POST (fallback)
            name = request.POST.get('user_name')
            phone_number = request.POST.get('phone_number')
            email = request.POST.get('user_email')
            total_person = request.POST.get('total_person')
            booking_data = request.POST.get('booking_data')

            # Validate the form data
            if name != '' and len(phone_number) == 10 and email != '' and total_person != '0' and booking_data != '':
                # Save the booking data to the database
                data = BookTable(Name=name, Phone_number=phone_number,
                                 Email=email, Total_person=total_person,
                                 Booking_date=booking_data)
                data.save()

                # Send confirmation email
                subject = 'Booking Confirmation'
                message = f"Hello {name},\n\nYour booking has been successfully received.\n" \
                          f"Booking details:\nTotal persons: {total_person}\n" \
                          f"Booking date: {booking_data}\n\nThank you for choosing us!"

                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [email]  # The email of the user

                # Send the confirmation email
                send_mail(subject, message, from_email, recipient_list)

                # Add success message
                messages.success(request, 'Booking request submitted successfully! Please check your confirmation email.')

                # Redirect or render a feedback page with success message
                return render(request, 'feedback.html', {'success': 'Booking request submitted successfully! Please check your confirmation email.'})

    # Render the book_table.html template and pass the API key to it
    return render(request, 'book_table.html', {'google_maps_api_key': google_maps_api_key})


def clear_cart(request):
    if request.method == 'POST' and request.user.is_authenticated:
        Cart.objects.filter(user=request.user).delete()
        return JsonResponse({'message': 'Cart cleared'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

def checkout(request):
    if request.method == 'POST' and request.user.is_authenticated:
        # Get cart items
        cart_items = Cart.objects.filter(user=request.user).select_related('item')
        if not cart_items:
            return JsonResponse({'error': 'Cart is empty'}, status=400)

        # Calculate total bill
        total_bill = sum(cart_item.quantity * cart_item.item.Price for cart_item in cart_items)

        # Prepare email content
        subject = 'Your Order Confirmation and Bill'
        message = f"Hello {request.user.username},\n\n" \
                  f"Thank you for your order!\n\n" \
                  f"Order Details:\n"

        for cart_item in cart_items:
            message += f"- {cart_item.item.Item_name} x {cart_item.quantity} = ${cart_item.quantity * cart_item.item.Price}\n"

        message += f"\nTotal Bill: ${total_bill}\n\n" \
                   f"We look forward to serving you!\n\n" \
                   f"Best regards,\nBurger Restaurant"

        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [request.user.email]

        # Send the email
        try:
            send_mail(subject, message, from_email, recipient_list)
        except Exception as e:
            print(f"Email sending failed: {e}")
            return JsonResponse({'error': 'Failed to send email'}, status=500)

        # Clear the cart
        Cart.objects.filter(user=request.user).delete()

        return JsonResponse({'message': 'Your order has been confirmed and the bill is sent to your email!'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

def FeedbackView(request):
    if request.method == 'POST':
        # Get data from the form
        name = request.POST.get('User_name')
        feedback = request.POST.get('Description')  # Assuming 'Feedback' field is a description
        rating = request.POST.get('Rating')
        image = request.FILES.get('Selfie')  # 'Selfie' field from the form

        # Print to check the values
        print('-->', name, feedback, rating, image)

        # Check if the name is provided
        if name != '':
            # Save the feedback data to the Feedback model
            feedback_data = Feedback(
                User_name=name,
                Description=feedback,
                Rating=rating,
                Image=image  # Save the uploaded image
            )
            feedback_data.save()

            # Add success message
            messages.success(request, 'Feedback submitted successfully!')

            # Optionally, you can redirect or return a success message
            return render(request, 'feedback.html', {'success': 'Feedback submitted successfully!'})

    return render(request, 'feedback.html')

