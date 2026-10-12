from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class RegisterForm(FlaskForm):
    display_name = StringField("Display name", validators=[DataRequired(), Length(2, 120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    county_id = SelectField("County (optional)", coerce=int, validators=[Optional()])
    preferred_language_id = SelectField(
        "Preferred language (optional)", coerce=int, validators=[Optional()]
    )
    preferred_dialect_id = SelectField(
        "Preferred dialect (optional)", coerce=int, validators=[Optional()]
    )
    consent = BooleanField("I agree for my contributions to be used in this project")
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign in")


class ProfileForm(FlaskForm):
    display_name = StringField("Display name", validators=[DataRequired(), Length(2, 120)])
    county_id = SelectField("County (optional)", coerce=int, validators=[Optional()])
    preferred_language_id = SelectField(
        "Preferred language (optional)", coerce=int, validators=[Optional()]
    )
    preferred_dialect_id = SelectField(
        "Preferred dialect (optional)", coerce=int, validators=[Optional()]
    )
    submit = SubmitField("Save changes")


class SubmissionForm(FlaskForm):
    language_id = SelectField("Language", coerce=int, validators=[DataRequired()])
    dialect_id = SelectField("Dialect / community (optional)", coerce=int,
                             validators=[Optional()])
    text = TextAreaField("Your translation", validators=[DataRequired(), Length(2, 2000)])
    usage_note = TextAreaField(
        "How is this used or understood in your community? (optional)",
        validators=[Optional(), Length(max=4000)],
    )
    example = TextAreaField(
        "Example of how a warning would be said in your language (optional)",
        validators=[Optional(), Length(max=4000)],
    )
    submit = SubmitField("Submit translation")


class ReviewForm(FlaskForm):
    action = SelectField(
        "Decision",
        choices=[
            ("approve", "Approve as canonical"),
            ("request_revision", "Request revision"),
            ("flag", "Flag as misleading / needs review"),
            ("reject", "Reject"),
        ],
        validators=[DataRequired()],
    )
    definition = TextAreaField("Definition to publish (optional)", validators=[Optional()])
    context = TextAreaField("Context / usage notes (optional)", validators=[Optional()])
    note = TextAreaField("Reviewer note (recorded in history)", validators=[Optional()])
    submit = SubmitField("Submit decision")


class VoteForm(FlaskForm):
    value = SelectField(
        "Your assessment",
        choices=[("support", "This communicates the meaning well"),
                 ("oppose", "This does not communicate the meaning")],
        validators=[DataRequired()],
    )
    submit = SubmitField("Record assessment")


class TermForm(FlaskForm):
    english_name = StringField("English name", validators=[DataRequired()])
    category = SelectField(
        "Category",
        choices=[("glossary", "Glossary term"), ("message", "Awareness message")],
        validators=[DataRequired()],
    )
    english_definition = TextAreaField("English definition", validators=[DataRequired()])
    swahili_name = StringField("Kiswahili name (optional)", validators=[Optional()])
    swahili_definition = TextAreaField("Kiswahili definition (optional)",
                                       validators=[Optional()])
    submit = SubmitField("Save term")
