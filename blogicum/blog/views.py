from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone

from .forms import CommentForm, PostForm, UserForm
from .models import Comment, Post, Category


def sort_posts(objects):
    return objects.order_by(*Post._meta.ordering)


def index(request):
    template = 'blog/index.html'
    # Получение всех постов
    posts = sort_posts(
        Post.objects.select_related(
            'author'
        ).select_related(
            'category'
        ).filter(
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True
        ).annotate(
            comment_count=Count('comment')
        )
    )
    # Пагинация по 10 страниц
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    context = {'page_obj': paginator.get_page(page_number)}
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'blog/detail.html'
    # Получение поста
    if request.user.is_authenticated:
        post = get_object_or_404(Post.objects.select_related(
            'author'
        ).select_related(
            'category'
        ).filter(
            Q(is_published=True)
            & Q(pub_date__lte=timezone.now())
            & Q(category__is_published=True)
            | Q(author__username=request.user.username)
        ), pk=post_id)
    else:
        post = get_object_or_404(Post.objects.select_related(
            'author'
        ).select_related(
            'category'
        ).filter(
            Q(is_published=True)
            & Q(pub_date__lte=timezone.now())
            & Q(category__is_published=True)
        ), pk=post_id)
    # Форма для отправки комментария
    form = CommentForm()
    # Получение всех комментариев поста
    comments = Comment.objects.select_related(
        'author'
    ).select_related(
        'post'
    ).filter(
        post__pk=post.pk
    )
    context = {
        'post': post,
        'form': form,
        'comments': comments,
    }
    return render(request, template, context)


def category_posts(request, category_slug):
    template = "blog/category.html"
    # Получение категории по её слагу
    category = get_object_or_404(
        Category.objects.filter(is_published=True),
        slug=category_slug
    )
    # Получение всех постов данной категории
    posts = sort_posts(
        Post.objects.select_related(
            'author'
        ).select_related(
            'category'
        ).filter(
            category__slug=category_slug,
            is_published=True,
            pub_date__lte=timezone.now()
        ).annotate(
            comment_count=Count('comment')
        )
    )
    # Пагинация по 10 страниц
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    context = {
        'page_obj': paginator.get_page(page_number),
        'category': category,
    }
    return render(request, template, context)


def user_profile(request, username):
    template = 'blog/profile.html'
    # Получение информации о пользователе
    User = get_user_model()
    user = get_object_or_404(
        User.objects,
        username=username
    )
    # Получение информации о постах пользователя
    posts = sort_posts(
        Post.objects.select_related(
            'author'
        ).select_related(
            'category'
        ).filter(
            author__username=username,
        ).annotate(
            comment_count=Count('comment')
        )
    )
    if request.user.is_authenticated and request.user.username != username:
        posts = posts.filter(
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True
        )
    # Пагинация постов
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    context = {
        'profile': user,
        'page_obj': paginator.get_page(page_number),
    }
    return render(request, template, context)


@login_required
def edit_profile(request):
    template = 'blog/user.html'
    # Получение информации о пользователе
    User = get_user_model()
    user = get_object_or_404(
        User.objects,
        username=request.user.username
    )
    form = UserForm(
        request.POST or None,
        instance=user
    )
    context = {'form': form}
    if request.method == 'POST':
        form.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, template, context)


@login_required
def create_post(request):
    template = 'blog/create.html'
    # Создание/валидация формы
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    context = {'form': form}
    # Сохранение публикации в базу данных
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, template, context)


@login_required
def edit_post(request, post_id):
    template = 'blog/create.html'
    # Получение поста и сравнивание его автора с пользователем
    post = get_object_or_404(
        Post.objects,
        pk=post_id
    )
    if request.user.username != post.author.username:
        return redirect('blog:post_detail', post_id=post_id)
    # Создание/проверка корректности формы
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    context = {'form': form}
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    form = CommentForm(request.POST or None)
    if form.is_valid():
        post = get_object_or_404(Post.objects, pk=post_id)
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    template = 'blog/comment.html'
    post = get_object_or_404(Post.objects, pk=post_id)
    comment = get_object_or_404(Comment.objects.filter(
        post_id=post.id,
        author=request.user
    ), pk=comment_id)
    form = CommentForm(
        request.POST or None,
        instance=comment
    )
    context = {
        'form': form,
        'comment': comment,
    }
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, template, context)


@login_required
def delete_post(request, post_id):
    template = 'blog/create.html'
    post = get_object_or_404(Post.objects.filter(
        author=request.user,
    ), pk=post_id)
    form = PostForm(instance=post)
    context = {'form': form}
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)
    return render(request, template, context)


@login_required
def delete_comment(request, post_id, comment_id):
    template = 'blog/comment.html'
    post = get_object_or_404(Post.objects, pk=post_id)
    comment = get_object_or_404(Comment.objects.filter(
        post_id=post.id,
        author=request.user
    ), pk=comment_id)
    context = {
        'comment': comment,
    }
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, template, context)
