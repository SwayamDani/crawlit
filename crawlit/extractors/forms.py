#!/usr/bin/env python3
"""
forms.py - Form detection and extraction

Extracts and analyzes HTML forms with detailed field information.
"""

import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


@dataclass
class FormField:
    """Represents a form field"""
    name: str
    field_type: str  # text, email, password, hidden, select, textarea, etc.
    label: Optional[str] = None
    value: Optional[str] = None
    placeholder: Optional[str] = None
    required: bool = False
    readonly: bool = False
    disabled: bool = False
    maxlength: Optional[int] = None
    minlength: Optional[int] = None
    pattern: Optional[str] = None
    options: List[str] = field(default_factory=list)  # For select/radio/checkbox
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class Form:
    """Represents an HTML form"""
    action: str
    method: str  # GET, POST, etc.
    enctype: Optional[str] = None
    form_id: Optional[str] = None
    form_class: Optional[str] = None
    name: Optional[str] = None
    fields: List[FormField] = field(default_factory=list)
    has_file_upload: bool = False
    has_captcha: bool = False
    has_csrf_token: bool = False
    submit_button_text: Optional[str] = None
    fieldsets: List[str] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)


class FormExtractor:
    """
    Extracts and analyzes HTML forms.
    
    Features:
    - Comprehensive field extraction
    - Field type detection
    - Label association
    - Validation attribute extraction
    - CAPTCHA detection
    - CSRF token detection
    - File upload detection
    """
    
    # CSRF token patterns
    CSRF_PATTERNS = {
        'csrf', 'csrftoken', '_csrf', 'authenticity_token',
        '_token', 'xsrf', 'xsrftoken', '_xsrf',
        '__RequestVerificationToken', 'form_build_id', '_wpnonce'
    }
    
    # CAPTCHA indicators
    CAPTCHA_INDICATORS = {
        'captcha', 'recaptcha', 'g-recaptcha', 'h-captcha',
        'hcaptcha', 'securimage', 'captchaimage'
    }
    
    def __init__(self, html_content: str, base_url: str = ""):
        """
        Initialize form extractor.
        
        Args:
            html_content: HTML content to extract forms from
            base_url: Base URL for resolving relative action URLs
        """
        self.html_content = html_content
        self.base_url = base_url
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.forms: List[Form] = []
        self.labels_map: Dict[str, str] = {}  # field_id -> label_text
    
    def extract_all_forms(self) -> List[Form]:
        """
        Extract all forms from the page.
        
        Returns:
            List of Form objects
        """
        self.forms = []
        
        # Build label map first
        self._build_label_map()
        
        # Extract each form
        form_elements = self.soup.find_all('form')
        
        for form_elem in form_elements:
            form = self._extract_form(form_elem)
            self.forms.append(form)
        
        logger.info(f"Extracted {len(self.forms)} form(s) from page")
        
        return self.forms
    
    def _build_label_map(self):
        """Build a map of field IDs to their labels"""
        for label in self.soup.find_all('label'):
            # Check for 'for' attribute
            field_id = label.get('for')
            if field_id:
                self.labels_map[field_id] = label.get_text(strip=True)
    
    def _extract_form(self, form_elem) -> Form:
        """Extract a single form"""
        # Get form attributes
        action = form_elem.get('action', '')
        if action and self.base_url:
            action = urljoin(self.base_url, action)
        
        method = form_elem.get('method', 'GET').upper()
        enctype = form_elem.get('enctype')
        form_id = form_elem.get('id')
        form_class = ' '.join(form_elem.get('class', []))
        name = form_elem.get('name')
        
        # Create form object
        form = Form(
            action=action,
            method=method,
            enctype=enctype,
            form_id=form_id,
            form_class=form_class,
            name=name,
            attributes={k: v for k, v in form_elem.attrs.items()}
        )
        
        # Extract fields
        form.fields = self._extract_fields(form_elem)
        
        # Detect special features
        form.has_file_upload = any(f.field_type == 'file' for f in form.fields)
        form.has_csrf_token = self._detect_csrf_token(form.fields)
        form.has_captcha = self._detect_captcha(form_elem)
        
        # Get submit button text
        form.submit_button_text = self._get_submit_button_text(form_elem)
        
        # Extract fieldsets
        form.fieldsets = [
            fs.find('legend').get_text(strip=True) if fs.find('legend') else ''
            for fs in form_elem.find_all('fieldset')
        ]
        
        return form
    
    def _extract_fields(self, form_elem) -> List[FormField]:
        """Extract all fields from a form"""
        fields = []
        
        # Extract input fields
        for input_elem in form_elem.find_all('input'):
            field = self._extract_input_field(input_elem)
            if field:
                fields.append(field)
        
        # Extract select fields
        for select_elem in form_elem.find_all('select'):
            field = self._extract_select_field(select_elem)
            if field:
                fields.append(field)
        
        # Extract textarea fields
        for textarea_elem in form_elem.find_all('textarea'):
            field = self._extract_textarea_field(textarea_elem)
            if field:
                fields.append(field)
        
        return fields
    
    def _extract_input_field(self, input_elem) -> Optional[FormField]:
        """Extract an input field"""
        field_type = input_elem.get('type', 'text').lower()
        name = input_elem.get('name')
        
        # Skip submit/button/image inputs (not data fields)
        if field_type in ['submit', 'button', 'image', 'reset']:
            return None
        
        if not name:
            return None
        
        field_id = input_elem.get('id')
        label = self.labels_map.get(field_id) if field_id else None
        
        # If no label found via 'for', check for parent label
        if not label:
            parent_label = input_elem.find_parent('label')
            if parent_label:
                label = parent_label.get_text(strip=True)
                # Remove the input's value from label text
                label = label.replace(input_elem.get('value', ''), '').strip()
        
        field = FormField(
            name=name,
            field_type=field_type,
            label=label,
            value=input_elem.get('value'),
            placeholder=input_elem.get('placeholder'),
            required=input_elem.has_attr('required'),
            readonly=input_elem.has_attr('readonly'),
            disabled=input_elem.has_attr('disabled'),
            pattern=input_elem.get('pattern'),
            attributes={k: v for k, v in input_elem.attrs.items()}
        )
        
        # Handle maxlength/minlength
        try:
            if input_elem.has_attr('maxlength'):
                field.maxlength = int(input_elem['maxlength'])
            if input_elem.has_attr('minlength'):
                field.minlength = int(input_elem['minlength'])
        except (ValueError, TypeError):
            pass
        
        # For radio/checkbox, extract options from similar inputs
        if field_type in ['radio', 'checkbox']:
            field.options = self._get_radio_checkbox_options(input_elem)
        
        return field
    
    def _extract_select_field(self, select_elem) -> Optional[FormField]:
        """Extract a select field"""
        name = select_elem.get('name')
        if not name:
            return None
        
        field_id = select_elem.get('id')
        label = self.labels_map.get(field_id) if field_id else None
        
        if not label:
            parent_label = select_elem.find_parent('label')
            if parent_label:
                label = parent_label.get_text(strip=True)
        
        # Extract options
        options = []
        selected_value = None
        for option in select_elem.find_all('option'):
            option_value = option.get('value', option.get_text(strip=True))
            options.append(option_value)
            if option.has_attr('selected'):
                selected_value = option_value
        
        field = FormField(
            name=name,
            field_type='select',
            label=label,
            value=selected_value,
            required=select_elem.has_attr('required'),
            disabled=select_elem.has_attr('disabled'),
            options=options,
            attributes={k: v for k, v in select_elem.attrs.items()}
        )
        
        return field
    
    def _extract_textarea_field(self, textarea_elem) -> Optional[FormField]:
        """Extract a textarea field"""
        name = textarea_elem.get('name')
        if not name:
            return None
        
        field_id = textarea_elem.get('id')
        label = self.labels_map.get(field_id) if field_id else None
        
        if not label:
            parent_label = textarea_elem.find_parent('label')
            if parent_label:
                label = parent_label.get_text(strip=True)
        
        field = FormField(
            name=name,
            field_type='textarea',
            label=label,
            value=textarea_elem.get_text(strip=True) or None,
            placeholder=textarea_elem.get('placeholder'),
            required=textarea_elem.has_attr('required'),
            readonly=textarea_elem.has_attr('readonly'),
            disabled=textarea_elem.has_attr('disabled'),
            attributes={k: v for k, v in textarea_elem.attrs.items()}
        )
        
        # Handle maxlength
        try:
            if textarea_elem.has_attr('maxlength'):
                field.maxlength = int(textarea_elem['maxlength'])
        except (ValueError, TypeError):
            pass
        
        return field
    
    def _get_radio_checkbox_options(self, input_elem) -> List[str]:
        """Get all options for a radio/checkbox group"""
        name = input_elem.get('name')
        form = input_elem.find_parent('form')
        
        if not form or not name:
            return []
        
        options = []
        for similar in form.find_all('input', {'name': name}):
            value = similar.get('value', '')
            if value:
                options.append(value)
        
        return options
    
    def _detect_csrf_token(self, fields: List[FormField]) -> bool:
        """Detect if form has CSRF token"""
        for field in fields:
            if field.field_type == 'hidden':
                if any(pattern in field.name.lower() for pattern in self.CSRF_PATTERNS):
                    return True
        return False
    
    def _detect_captcha(self, form_elem) -> bool:
        """Detect if form has CAPTCHA"""
        # Check for CAPTCHA-related elements
        form_html = str(form_elem).lower()
        
        for indicator in self.CAPTCHA_INDICATORS:
            if indicator in form_html:
                return True
        
        # Check for common CAPTCHA classes/ids
        for elem in form_elem.find_all(['div', 'iframe', 'script']):
            elem_id = (elem.get('id', '') + ' ' + ' '.join(elem.get('class', []))).lower()
            if any(indicator in elem_id for indicator in self.CAPTCHA_INDICATORS):
                return True
        
        return False
    
    def _get_submit_button_text(self, form_elem) -> Optional[str]:
        """Get submit button text"""
        # Check input[type=submit]
        submit_input = form_elem.find('input', {'type': 'submit'})
        if submit_input:
            return submit_input.get('value', 'Submit')
        
        # Check button[type=submit] or button without type
        submit_button = form_elem.find('button', {'type': 'submit'})
        if not submit_button:
            submit_button = form_elem.find('button')
        
        if submit_button:
            return submit_button.get_text(strip=True)
        
        return None
    
    def get_form_by_id(self, form_id: str) -> Optional[Form]:
        """Get a form by its ID"""
        if not self.forms:
            self.extract_all_forms()
        
        for form in self.forms:
            if form.form_id == form_id:
                return form
        return None
    
    def get_forms_by_action(self, action_pattern: str) -> List[Form]:
        """Get forms by action URL pattern"""
        if not self.forms:
            self.extract_all_forms()
        
        return [f for f in self.forms if action_pattern in f.action]
    
    def get_login_forms(self) -> List[Form]:
        """Heuristically identify login forms"""
        if not self.forms:
            self.extract_all_forms()
        
        login_forms = []
        
        for form in self.forms:
            # Check if form has password field
            has_password = any(f.field_type == 'password' for f in form.fields)
            
            # Check if action/id/class suggests login
            login_indicators = ['login', 'signin', 'sign-in', 'auth']
            form_text = (form.action + ' ' + (form.form_id or '') + ' ' + 
                        (form.form_class or '')).lower()
            has_login_indicator = any(indicator in form_text for indicator in login_indicators)
            
            if has_password and (has_login_indicator or len(form.fields) <= 5):
                login_forms.append(form)
        
        return login_forms
    
    def get_search_forms(self) -> List[Form]:
        """Heuristically identify search forms"""
        if not self.forms:
            self.extract_all_forms()
        
        search_forms = []
        search_indicators = ['search', 'query', 'q', 'find']
        
        for form in self.forms:
            # Check action/id/class
            form_text = (form.action + ' ' + (form.form_id or '') + ' ' + 
                        (form.form_class or '')).lower()
            
            # Check field names
            field_names = ' '.join(f.name.lower() for f in form.fields)
            
            combined = form_text + ' ' + field_names
            
            if any(indicator in combined for indicator in search_indicators):
                search_forms.append(form)
        
        return search_forms
    
    def to_dict(self) -> List[Dict[str, Any]]:
        """Convert extracted forms to dictionaries"""
        if not self.forms:
            self.extract_all_forms()
        
        return [self._form_to_dict(form) for form in self.forms]
    
    def _form_to_dict(self, form: Form) -> Dict[str, Any]:
        """Convert a Form to dictionary"""
        return {
            'action': form.action,
            'method': form.method,
            'enctype': form.enctype,
            'id': form.form_id,
            'class': form.form_class,
            'name': form.name,
            'fields': [self._field_to_dict(f) for f in form.fields],
            'has_file_upload': form.has_file_upload,
            'has_captcha': form.has_captcha,
            'has_csrf_token': form.has_csrf_token,
            'submit_button_text': form.submit_button_text,
            'fieldsets': form.fieldsets,
            'field_count': len(form.fields)
        }
    
    def _field_to_dict(self, field: FormField) -> Dict[str, Any]:
        """Convert a FormField to dictionary"""
        return {
            'name': field.name,
            'type': field.field_type,
            'label': field.label,
            'value': field.value,
            'placeholder': field.placeholder,
            'required': field.required,
            'readonly': field.readonly,
            'disabled': field.disabled,
            'maxlength': field.maxlength,
            'minlength': field.minlength,
            'pattern': field.pattern,
            'options': field.options if field.options else None
        }


def extract_forms(html_content: str, base_url: str = "") -> List[Form]:
    """
    Convenience function to extract forms.
    
    Args:
        html_content: HTML content
        base_url: Base URL for resolving relative URLs
        
    Returns:
        List of Form objects
    """
    extractor = FormExtractor(html_content, base_url)
    return extractor.extract_all_forms()



