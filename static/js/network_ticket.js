jQuery(document).ready(function() {
	jQuery('#add_id_ticket_types').attr('href', jQuery('#add_id_ticket_types').attr('href') + '&network_ticket=1');
})
jQuery(document).ready(function() {
	jQuery('#changelist-search input[type=text]').after(jQuery('#changelist-search input[type=submit]'));
	jQuery('#changelist-search input[type=submit]').after(jQuery('<div></div>'));
})
