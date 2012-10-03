from feincms.models import Base, Template as FeinCMSTemplate
from feincms.module.page.models import Page
from feincms.content.richtext.models import RichTextContent


class Template(FeinCMSTemplate):
    def __init__(
        self, title, path, regions, key=None, preview_image=None, unique=False
    ):
        super(Template, self).__init__(
            title, path, regions, key=key, preview_image=preview_image
        )
        self.unique = unique


Page.register_templates(
    Template(
        key='internalpage',
        title='Internal Page',
        path='pages/internal.html',
        regions=(
            ('main', 'Main Content'),
        )
    ), Template(
        key='homepage',
        title='Home Page',
        path='pages/home_page.html',
        regions=(
            ('home_main', 'Main Content'),
        ),
        unique=True
    )
)

Page.create_content_type(RichTextContent)