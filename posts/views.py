from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.template.loader import render_to_string
from .models import Post, Comment
from .forms import PostForm, CommentForm
from accounts.models import User  # Custom user model


@login_required
def feed(request):
    """Role-aware feed with dynamic liking/commenting"""
    
    # Handle new post submission
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "✅ Post created successfully!")
            return redirect("feed")
    else:
        form = PostForm()

    # Role-aware feed
    following_users = request.user.following.all()
    
    if request.user.role == "player":
        posts = Post.objects.filter(
            Q(author=request.user) | Q(author__in=following_users)
        ).order_by("-created_at")
    elif request.user.role == "scout":
        posts = Post.objects.filter(
            author__role="player",
            author__in=following_users
        ).order_by("-created_at")
    elif request.user.role == "club":
        posts = Post.objects.filter(
            Q(author__role="player") | Q(author__role="scout")
        ).order_by("-created_at")
    else:
        posts = Post.objects.none()

    comment_form = CommentForm()

    context = {
        "form": form,
        "posts": posts,
        "comment_form": comment_form,
    }
    return render(request, "posts/feeds.html", context)


@login_required
def like_post(request, post_id):
    """AJAX: Toggle like/unlike"""
    post = get_object_or_404(Post, id=post_id)
    user = request.user
    if user in post.likes.all():
        post.likes.remove(user)
        liked = False
    else:
        post.likes.add(user)
        liked = True
    return JsonResponse({
        "liked": liked,
        "total_likes": post.total_likes(),
    })


@login_required
def add_comment(request, post_id):
    """AJAX: Add comment to post"""
    if request.method == "POST":
        post = get_object_or_404(Post, id=post_id)
        content = request.POST.get("content", "").strip()
        if content:
            comment = Comment.objects.create(post=post, author=request.user, content=content)
            return JsonResponse({
                "author": comment.author.username,
                "content": comment.content,
                "total_comments": post.comments.count(),
            })
    return JsonResponse({"error": "Invalid request"})


@login_required
def repost_post(request, post_id):
    """Allow a scout (or any user) to repost a player's post"""
    original = get_object_or_404(Post, id=post_id)

    # prevent duplicate reposts by same user
    if Post.objects.filter(author=request.user, original_post=original).exists():
        messages.info(request, "You already reposted this post.")
        return redirect("scout_dashboard")

    Post.objects.create(
        author=request.user,
        original_post=original,
        content=f"🔁 Repost from {original.author.username}",
    )

    messages.success(request, "Post successfully reposted.")
    return redirect("scout_dashboard")

@login_required
def fetch_new_posts(request):
    """AJAX: Return new posts since last post ID"""
    last_post_id = request.GET.get("last_post_id", 0)
    new_posts = Post.objects.filter(id__gt=last_post_id).order_by("-created_at")

    html = render_to_string("posts/partials/post_list.html", {"posts": new_posts}, request=request)
    return JsonResponse({"html": html})