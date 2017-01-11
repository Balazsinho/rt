jQuery(document).ready(function() {
	jQuery('#changelist-search input[type=text]').after(jQuery('#changelist-search input[type=submit]'));
	jQuery('#changelist-search input[type=submit]').after(jQuery('<div></div>'));
})