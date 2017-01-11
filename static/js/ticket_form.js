var closed_stat;

function displayClosedAt() {
	var curr_stat = jQuery('#select2-id_status-container').attr('title');
	var row = jQuery('#id_closed_at').parent().parent();
	if (closed_stat.indexOf(curr_stat) > -1) {
		row.show();
	} else {
		row.hide();
	}
}

function siteSpecificEvents(context) {
	jQuery(document).ready(function() {
		closed_stat = context['closed_statuses'];
		displayClosedAt();
		jQuery('#id_status').change(
			function() { displayClosedAt() }
		)
	});
}