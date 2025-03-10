from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone

from .forms import CommentForm, PostForm, UserForm
from .models import Comment, Post, Category


def index(request):
    template = 'blog/index.html'
    # Получение всех постов
    posts = Post.objects.select_related(
        'author'
    ).select_related(
        'category'
    ).filter(
        pub_date__lte=timezone.now(),
        is_published=True,
        category__is_published=True
    ).annotate(
        comment_count=Count('comment')
    ).order_by('-pub_date')
    # Пагинация по 10 страниц
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    context = {'page_obj': paginator.get_page(page_number)}
    return render(request, template, context)


def post_detail(request, id):
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
        ), pk=id)
    else:
        post = get_object_or_404(Post.objects.select_related(
            'author'
        ).select_related(
            'category'
        ).filter(
            Q(is_published=True)
            & Q(pub_date__lte=timezone.now())
            & Q(category__is_published=True)
        ), pk=id)
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
    posts = Post.objects.select_related(
        'author'
    ).select_related(
        'category'
    ).filter(
        category__slug=category_slug,
        is_published=True,
        pub_date__lte=timezone.now()
    ).annotate(
        comment_count=Count('comment')
    ).order_by('-pub_date')
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
    posts = Post.objects.select_related(
        'author'
    ).select_related(
        'category'
    ).filter(
        author__username=username,
    ).annotate(
        comment_count=Count('comment')
    ).order_by('-pub_date')
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
        return redirect(reverse(
            'blog:profile',
            kwargs={'username': request.user.username}
        ))
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
        return redirect(reverse(
            'blog:profile',
            kwargs={'username': request.user.username}
        ))
    return render(request, template, context)


@login_required
def edit_post(request, id):
    template = 'blog/create.html'
    # Получение поста и сравнивание его автора с пользователем
    post = get_object_or_404(
        Post.objects,
        pk=id
    )
    if request.user.username != post.author.username:
        return redirect(reverse('blog:post_detail', kwargs={'id': id}))
    # Создание/проверка корректности формы
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    context = {'form': form}
    if form.is_valid():
        form.save()
        return redirect(reverse('blog:post_detail', kwargs={'id': id}))
    return render(request, template, context)


@login_required
def add_comment(request, id):
    form = CommentForm(request.POST or None)
    if form.is_valid():
        post = get_object_or_404(Post.objects, pk=id)
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect(reverse('blog:post_detail', kwargs={'id': id}))


@login_required
def edit_comment(request, id, comment_id):
    template = 'blog/comment.html'
    post = get_object_or_404(Post.objects, pk=id)
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
        return redirect(reverse('blog:post_detail', kwargs={'id': id}))
    return render(request, template, context)


@login_required
def delete_post(request, id):
    template = 'blog/create.html'
    post = get_object_or_404(Post.objects.filter(
        author=request.user,
    ), pk=id)
    form = PostForm(instance=post)
    context = {'form': form}
    if request.method == 'POST':
        post.delete()
        return redirect(reverse(
            'blog:profile',
            kwargs={'username': request.user.username}
        ))
    return render(request, template, context)


@login_required
def delete_comment(request, id, comment_id):
    template = 'blog/comment.html'
    post = get_object_or_404(Post.objects, pk=id)
    comment = get_object_or_404(Comment.objects.filter(
        post_id=post.id,
        author=request.user
    ), pk=comment_id)
    context = {
        'comment': comment,
    }
    if request.method == 'POST':
        comment.delete()
        return redirect(reverse('blog:post_detail', kwargs={'id': id}))
    return render(request, template, context)
