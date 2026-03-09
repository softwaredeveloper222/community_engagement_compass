from django import forms


class FeedbackForm(forms.Form):
    name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"placeholder": "Your name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "you@example.com"}))
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Your feedback..."}))


class SurveyFeedbackForm(forms.Form):
    EASE_CHOICES = [
        ("easy", "Easy"),
        ("neutral", "Neutral"),
        ("difficult", "Difficult"),
    ]

    RELEVANCE_CHOICES = [
        ("relevant", "Relevant"),
        ("neutral", "Neutral"),
        ("not_relevant", "Not relevant"),
    ]

    TRUST_CHOICES = [
        ("confident", "Confident"),
        ("neutral", "Neutral"),
        ("not_confident", "Not confident"),
    ]

    CITATIONS_CHOICES = [
        ("helpful", "Helpful"),
        ("neutral", "Neutral"),
        ("not_helpful", "Not helpful"),
    ]

    LIKELIHOOD_CHOICES = [
        ("likely", "Likely"),
        ("neutral", "Neutral"),
        ("unlikely", "Unlikely"),
    ]

    ease_of_use = forms.ChoiceField(choices=EASE_CHOICES, widget=forms.RadioSelect)
    relevance = forms.ChoiceField(choices=RELEVANCE_CHOICES, widget=forms.RadioSelect)
    trust = forms.ChoiceField(choices=TRUST_CHOICES, widget=forms.RadioSelect)
    citations_helpfulness = forms.ChoiceField(choices=CITATIONS_CHOICES, widget=forms.RadioSelect)
    likelihood_of_use = forms.ChoiceField(choices=LIKELIHOOD_CHOICES, widget=forms.RadioSelect)
    additional_sources = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Optional: resources or frameworks to add"}))
    open_feedback = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4, "placeholder": "What worked well? What can be improved?"}))

