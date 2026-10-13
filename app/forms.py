from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Optional,
    Regexp,
)

USERNAME_RE = r"^[A-Za-z0-9_]+$"
USERNAME_HELP = "3–30 characters: letters, numbers and underscores only."


class RegisterForm(FlaskForm):
    display_name = StringField("Display name", validators=[DataRequired(), Length(2, 120)])
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(3, 30, message="Username must be 3–30 characters."),
            Regexp(USERNAME_RE, message=USERNAME_HELP),
        ],
    )
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
    identifier = StringField("Username or email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign in")


class ForgotPasswordForm(FlaskForm):
    identifier = StringField("Username or email", validators=[DataRequired()])
    submit = SubmitField("Send me a code")


class ResetPasswordForm(FlaskForm):
    code = StringField(
        "Verification code",
        validators=[DataRequired(), Length(6, 6, message="Enter the 6-digit code.")],
    )
    password = PasswordField(
        "New password",
        validators=[DataRequired(), Length(min=8, message="Use at least 8 characters.")],
    )
    confirm = PasswordField(
        "Confirm new password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Set new password")


class VerifyEmailForm(FlaskForm):
    email = StringField(
        "Email", validators=[DataRequired(), Email(), Length(max=255)]
    )
    code = StringField(
        "Verification code",
        validators=[DataRequired(), Length(6, 6, message="Enter the 6-digit code.")],
    )
    submit = SubmitField("Verify email")


class ResendVerificationForm(FlaskForm):
    email = StringField(
        "Email", validators=[DataRequired(), Email(), Length(max=255)]
    )
    submit = SubmitField("Resend code")


class ProfileForm(FlaskForm):
    display_name = StringField("Display name", validators=[DataRequired(), Length(2, 120)])
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(3, 30, message="Username must be 3–30 characters."),
            Regexp(USERNAME_RE, message=USERNAME_HELP),
        ],
    )
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
