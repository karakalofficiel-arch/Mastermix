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

#include "gtkmm2ext/actions.h"

#include "pt_edit_modes.h"

#include "pbd/i18n.h"

using namespace ArdourWidgets;

PTEditModes::PTEditModes ()
	: Gtk::Table (2, 2, true)
{
	set_row_spacings (1);
	set_col_spacings (1);

	setup (_shuffle, _("SHUFFLE"), "Editor", "set-edit-ripple");
	setup (_spot,    _("SPOT"),    "Editor", "set-edit-lock");
	setup (_slip,    _("SLIP"),    "Editor", "set-edit-slide");
	setup (_grid,    _("GRID"),    "Editing", "snap-magnetic");

	attach (_shuffle, 0, 1, 0, 1, Gtk::FILL, Gtk::FILL);
	attach (_spot,    1, 2, 0, 1, Gtk::FILL, Gtk::FILL);
	attach (_slip,    0, 1, 1, 2, Gtk::FILL, Gtk::FILL);
	attach (_grid,    1, 2, 1, 2, Gtk::FILL, Gtk::FILL);

	/* GRID toggles between snap-magnetic and snap-off; the related action
	 * only turns it on, the press handler turns it off */
	_grid.signal_button_press_event ().connect (sigc::mem_fun (*this, &PTEditModes::grid_press), false);

	show_all ();
}

void
PTEditModes::setup (ArdourButton& b, const char* text, const char* group, const char* name)
{
	b.set_text (text);
	b.set_name ("mouse mode button");
	b.set_related_action (ActionManager::get_action (group, name));
	b.set_sizing_text ("SHUFFLE");
}

bool
PTEditModes::grid_press (GdkEventButton* ev)
{
	if (ev->type == GDK_BUTTON_PRESS && ev->button == 1 && _grid.active_state () == Gtkmm2ext::ExplicitActive) {
		ActionManager::get_action ("Editing", "snap-off")->activate ();
		return true;
	}
	return false;
}

void
PTEditModes::sync (ARDOUR::EditMode em, Editing::SnapMode sm)
{
	_shuffle.set_active_state (em == ARDOUR::Ripple ? Gtkmm2ext::ExplicitActive : Gtkmm2ext::Off);
	_spot.set_active_state (em == ARDOUR::Lock ? Gtkmm2ext::ExplicitActive : Gtkmm2ext::Off);
	_slip.set_active_state (em == ARDOUR::Slide ? Gtkmm2ext::ExplicitActive : Gtkmm2ext::Off);
	_grid.set_active_state (sm != Editing::SnapOff ? Gtkmm2ext::ExplicitActive : Gtkmm2ext::Off);
}
