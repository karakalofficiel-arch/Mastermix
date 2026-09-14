/*
 * Copyright (C) 2026 Ahmed Hadjadj
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

#include "pbd/compose.h"
#include "pbd/controllable.h"

#include "ardour/amp.h"
#include "ardour/automation_control.h"
#include "ardour/meter.h"
#include "ardour/panner_manager.h"
#include "ardour/rc_configuration.h"
#include "ardour/send.h"
#include "ardour/session.h"

#include "gtkmm2ext/gtk_ui.h"

#include "pt_send_window.h"
#include "timers.h"
#include "ui_config.h"

#include "pbd/i18n.h"

using namespace ARDOUR;

#define PX_SCALE(px) std::max ((float)px, rintf ((float)px * UIConfiguration::instance ().get_ui_scale ()))

PTSendWindow::PTSendWindow (Session* session, std::shared_ptr<Send> s, const std::string& track_name)
	: ArdourWindow (string_compose (_("Send: %1 (%2)"), s->name (), track_name))
	, _send (s)
	, _gpm (session, 250)
	, _invert_button (X_("Ø"))
	, _panners (session)
{
	set_name ("SendUIWindow");

	uint32_t const in  = _send->pans_required ();
	uint32_t const out = _send->pan_outs ();

	_panners.set_width (Wide);
	_panners.set_available_panners (PannerManager::instance ().get_available_panners (in, out));
	_panners.set_panner (_send->panner_shell (), _send->panner ());
	_panners.setup_pan ();
	_panners.set_send_drawing_mode (true);
	_panners.set_size_request (PX_SCALE (200), PX_SCALE (70));

	_send->set_metering (true);

	_gpm.setup_meters ();
	_gpm.set_fader_name (X_("SendUIFader"));
	_gpm.set_controls (std::shared_ptr<Route> (), _send->meter (), _send->amp (), _send->gain_control ());

	_invert_button.set_controllable (_send->polarity_control ());
	_invert_button.watch ();
	_invert_button.set_name (X_("invert button"));
	_invert_button.signal_button_press_event ().connect (sigc::mem_fun (*this, &PTSendWindow::invert_press), false);
	_invert_button.signal_button_release_event ().connect (sigc::mem_fun (*this, &PTSendWindow::invert_release), false);
	Gtkmm2ext::UI::instance ()->set_tip (_invert_button, _("Click to invert polarity of all send channels"));

	_vbox.set_spacing (4);
	_vbox.pack_start (_invert_button, false, false);
	_vbox.pack_start (_panners, false, false);

	_hbox.set_spacing (6);
	_hbox.set_border_width (6);
	_hbox.pack_start (_gpm, false, false);
	_hbox.pack_start (_vbox, true, true);

	add (_hbox);
	_hbox.show_all ();

	_fast_screen_update_connection = Timers::super_rapid_connect (sigc::mem_fun (*this, &PTSendWindow::fast_update));
}

PTSendWindow::~PTSendWindow ()
{
	_fast_screen_update_connection.disconnect ();
	_send->set_metering (false);
}

void
PTSendWindow::fast_update ()
{
	if (!get_mapped ()) {
		return;
	}
	if (Config->get_meter_falloff () > 0.0f) {
		_gpm.update_meters ();
	}
}

bool
PTSendWindow::invert_press (GdkEventButton* ev)
{
	if (ArdourWidgets::BindingProxy::is_bind_action (ev)) {
		return false;
	}
	if (ev->button != 1 || ev->type == GDK_2BUTTON_PRESS || ev->type == GDK_3BUTTON_PRESS) {
		return true;
	}
	std::shared_ptr<AutomationControl> ac = _send->polarity_control ();
	if (!ac) {
		return true;
	}
	ac->start_touch (timepos_t (ac->session ().audible_sample ()));
	return true;
}

bool
PTSendWindow::invert_release (GdkEventButton* ev)
{
	if (ev->button != 1 || ev->type == GDK_2BUTTON_PRESS || ev->type == GDK_3BUTTON_PRESS) {
		return true;
	}
	std::shared_ptr<AutomationControl> ac = _send->polarity_control ();
	if (!ac) {
		return true;
	}
	ac->set_value (_invert_button.get_active () ? 0 : 1, PBD::Controllable::NoGroup);
	ac->stop_touch (timepos_t (ac->session ().audible_sample ()));
	return true;
}
