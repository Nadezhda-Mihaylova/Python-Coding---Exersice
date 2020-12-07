from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, FormView, UpdateView

from advanture_app import models
from advanture_app.forms import FilterForm, CommentForm, ArticleCreateForm
from advanture_app.models import Article, Comment, Like
from adventure_core.clean_up import clean_up_files
from adventure_core.view_mixins import GroupRequiredMixin


def extract_filter_values(params):
    order = params['order'] if 'order' in params else FilterForm.ORDER_ASC
    text = params['text'] if 'text' in params else ''

    return {
        'order': order,
        'text': text,
    }


class HomeView(ListView):
    template_name = 'home.html'
    model = Article
    context_object_name = 'articles'
    order_by_asc = True
    order_by = 'title'
    contains_text = ''

    def dispatch(self, request, *args, **kwargs):
        params = extract_filter_values(request.GET)
        self.order_by_asc = params['order'] == FilterForm.ORDER_ASC
        self.order_by = params['order']
        self.contains_text = params['text']
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        order_by = 'title' if self.order_by == FilterForm.ORDER_ASC else '-title'
        result = self.model.objects.filter(title__icontains=self.contains_text).order_by(order_by)

        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = FilterForm(initial={
            'order': self.order_by,
            'text': self.contains_text
        })

        return context


# def article_details(request, pk, slug=None):
@login_required
def article_details_or_comment(request, pk):
    article = Article.objects.get(pk=pk)
    if request.method == 'GET':
        context = {
            'article': article,
            'form': CommentForm(),
            'can_delete': request.user == article.user.user,
            'can_edit': request.user == article.user.user,
            'can_like': request.user != article.user.user,
            'has_liked': article.like_set.filter(article_id=request.user.userprofile.id).exists(),
            'can_comment': request.user != article.user.user,
            'author': article.user.user,
        }
        return render(request, 'article_details.html', context)
    else:
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = Comment(text=form.cleaned_data['text'])
            comment.article = article
            comment.user = request.user.userprofile
            comment.save()
            return redirect('article details or comment', pk)
        context = {
            'article': article,
            'form': form,
        }

        return render(request, 'article_details.html', context)


class ArticleCreateView(LoginRequiredMixin, FormView):  # GroupRequiredMixin
    form_class = ArticleCreateForm
    template_name = 'article_create.html'
    success_url = reverse_lazy('home')
    groups = ['User']

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


def unauthorised_message(request):
    return render(request, 'unauthorised.html')


def article_List(request):
    context = {
        'articles': Article.objects.all(),
    }

    return render(request, 'article_list.html', context)


def edit_article(request, pk):
    article = Article.objects.get(pk=pk)
    if request.method == 'GET':
        form = ArticleCreateForm(instance=article)

        context = {
            'form': form,
            'article': article,
        }

        return render(request, f'article_edit.html', context)
    else:
        old_image = article.image
        form = ArticleCreateForm(
            request.POST,
            request.FILES,
            instance=article
        )
        if form.is_valid():
            if old_image:
                clean_up_files(old_image.path)
            form.save()
            Like.objects.filter(article_id=article.id) \
                .delete()
            return redirect('article details or comment', article.pk)

        context = {
            'form': form,
            'article': article,
        }
    return render(request, 'article_edit.html', article)


@login_required
def delete_article(request, pk):
    article = Article.objects.get(pk=pk)
    if article.user.user != request.user:
        pass
    if request.method == 'GET':
        context = {
            'article': article,
        }
        return render(request, 'article_delete.html', context)
    else:
        article.delete()
        return redirect('articles')


@login_required
def like_article(request, pk):
    like = Like.objects.filter(user_id=request.user.userprofile.id, article_id=pk).first()
    if like:
        like.delete()
    else:
        article = Article.objects.get(pk=pk)
        like = Like(test=str(pk), user=request.user.userprofile)
        like.article = article
        like.save()
    return redirect('article details or comment', pk)

